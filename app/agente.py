"""Agente Fundalis IA — orquestração em LangGraph.

Grafo (o Mermaid é gerado daqui por `grafo.get_graph().draw_mermaid()` e exibido na aba Agente):

    carrega_memoria → guardrail_entrada ─┬─(bloqueado)→ bloqueio → FIM
                                         └─→ cache_semantico ─┬─(hit)→ resposta_cache → FIM
                                                              └─→ genie ∥ rag → sintese ─┬─(barrada)→ FIM
                                                                                         └─→ guardrail_saida → grava_memoria → FIM

- guardrail_entrada / guardrail_saida: prompts de guardrail no Opus 4.8 (model service do AI Gateway, registrados na
  inference table) + service policies do AI Gateway, quando houver.
- cache_semantico: memória do agente no Lakebase (pgvector), separada por escopo de acesso a PII.
- genie (tabelas + PDFs, on-behalf-of do usuário) e rag (busca vetorial no Lakebase) rodam em PARALELO.
- sintese: resposta final no Opus 4.8 só com o contexto recuperado.

As dependências (Genie, Lakebase, AI Gateway…) vêm do app via `construir_grafo(deps)`; os passos são emitidos ao
vivo com `get_stream_writer()` e chegam ao navegador como NDJSON.
"""
import json
import operator
from typing import Annotated, Any, Optional, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph


class Estado(TypedDict, total=False):
    pergunta: str
    conv_id: str
    genie_conv: Optional[str]
    usar_cache: bool
    hist: str
    guard: dict
    q: str
    escopo: str
    emb: Any
    docs: list
    genie: dict
    sql: Optional[str]
    resposta: str
    # escritos pelos ramos paralelos (genie ∥ rag) → precisam de reducer
    cards: Annotated[list, operator.add]
    fontes: Annotated[list, operator.add]
    usadas: Annotated[list, operator.add]
    final: dict


def _passo(pid, label, estado):
    get_stream_writer()({"tipo": "passo", "id": pid, "label": label, "estado": estado})


def construir_grafo(d):
    """`d` expõe: log, guardrail_entrada, msg_bloqueio, guardrail_saida, PolicyBlock, pii_liberado, embed,
    cache_busca, cache_grava, genie_space, genie_answer, rag_docs, gateway_chat, hist_carrega, hist_grava,
    agente_prompt, agent_service, define_usuario."""

    def no(fn):
        # nós paralelos rodam em threads: reaplica o usuário (OBO) do request em cada nó
        def _wrap(s, config):
            d.define_usuario(config)
            return fn(s)
        _wrap.__name__ = fn.__name__
        return _wrap

    def carrega_memoria(s):
        try:
            hist = d.hist_carrega(s["conv_id"])
        except Exception as e:  # noqa: BLE001
            d.log.warning("histórico indisponível: %s", e)
            hist = ""
        d.hist_grava(s["conv_id"], "user", s["pergunta"])
        return {"hist": hist}

    def guardrail_entrada(s):
        _passo("guard", "Guardrail de entrada (Opus 4.8 · AI Gateway)", "run")
        gd = d.guardrail_entrada(s["pergunta"], s.get("hist", ""))
        if gd["permitido"]:
            _passo("guard", f"Guardrail ok · assunto: {gd['assunto']}", "done")
        return {"guard": gd, "q": gd.get("pergunta_autonoma") or s["pergunta"]}

    def bloqueio(s):
        gd = s["guard"]
        pol = gd.get("policy")
        if pol:
            _passo("guard", f"Bloqueado pela service policy '{pol.get('name')}' do AI Gateway 🛡️ — {pol.get('reason') or ''}", "block")
            msg = ("Essa pergunta foi barrada pela política de segurança do AI Gateway da Fundalis. "
                   "Posso ajudar com fundição, peças, qualidade, vendas, leads, política comercial e operações. ⚙️")
        else:
            _passo("guard", f"Bloqueado pelo guardrail — {gd['assunto']} 🛡️", "block")
            msg = d.msg_bloqueio(gd)
        d.hist_grava(s["conv_id"], "assistant", msg, {"bloqueado": True, "assunto": gd["assunto"]})
        return {"final": {"resposta": msg, "bloqueado": True, "assunto": gd["assunto"], "motivo": gd.get("motivo"),
                          "ferramentas": ["Guardrail"]}}

    def cache_semantico(s):
        escopo = "pii" if d.pii_liberado() else "mascarado"
        emb = None
        try:
            emb = d.embed([s["q"]])[0]
        except Exception as e:  # noqa: BLE001
            d.log.warning("embedding da pergunta: %s", e)
        if not s.get("usar_cache", True) or emb is None:
            return {"escopo": escopo, "emb": emb}
        _passo("cache", "Memória do agente · cache semântico (Lakebase)", "run")
        try:
            hit = d.cache_busca(emb, escopo, s["q"])
        except Exception as e:  # noqa: BLE001
            d.log.warning("cache: %s", e)
            hit = None
        if not hit:
            _passo("cache", "Sem resposta equivalente em cache", "skip")
            return {"escopo": escopo, "emb": emb}
        sim = round(1 - float(hit["dist"]), 3)
        _passo("cache", f"Resposta em cache (similaridade {sim}) ⚡", "done")
        r = hit["resposta"] if isinstance(hit["resposta"], dict) else json.loads(hit["resposta"])
        return {"escopo": escopo, "emb": emb,
                "final": {**r, "cache": {"hit": True, "similaridade": sim, "pergunta_original": hit["pergunta"]},
                          "assunto": s["guard"]["assunto"], "ferramentas": ["Cache Lakebase"] + (r.get("ferramentas") or [])}}

    def resposta_cache(s):
        d.hist_grava(s["conv_id"], "assistant", s["final"].get("resposta", ""), {"cache": True})
        return {}

    def genie(s):
        gsid = d.genie_space() if s["guard"].get("precisa_dados", True) else None
        if not gsid:
            return {"genie": {}}
        _passo("genie", "Genie · consultando tabelas e documentos (OBO)", "run")
        try:
            g = d.genie_answer(s["q"], gsid, s.get("genie_conv")) or {}
        except Exception as e:  # noqa: BLE001
            d.log.warning("genie: %s", e)
            _passo("genie", "Genie indisponível", "skip")
            return {"genie": {}}
        cards = [{"tipo": "tabela", "colunas": g["colunas"], "linhas": g["linhas"][:12]}] if g.get("colunas") and g.get("linhas") else []
        _passo("genie", "Genie · resposta obtida", "done")
        return {"genie": g, "sql": g.get("sql"), "genie_conv": g.get("conv_id") or s.get("genie_conv"),
                "cards": cards, "usadas": ["Genie"]}

    def rag(s):
        _passo("rag", "RAG · busca vetorial nos PDFs (Lakebase pgvector)", "run")
        try:
            docs = [x for x in d.rag_docs(s["q"], k=6, emb=s.get("emb")) if float(x["similaridade"]) >= 0.35]
        except Exception as e:  # noqa: BLE001
            d.log.warning("rag: %s", e)
            _passo("rag", "RAG indisponível", "skip")
            return {"docs": []}
        _passo("rag", f"RAG · {len(docs)} trecho(s) relevante(s)", "done" if docs else "skip")
        return {"docs": docs, "usadas": ["Documentos (RAG)"] if docs else [],
                "fontes": [{"tipo": "DOC", "arquivo": x["arquivo"], "pagina": x["pagina"], "secao": x["secao"],
                            "similaridade": float(x["similaridade"])} for x in docs]}

    def sintese(s):
        _passo("resp", "Redigindo a resposta (Opus 4.8)", "run")
        g, q, pergunta, hist = s.get("genie") or {}, s["q"], s["pergunta"], s.get("hist", "")
        ctx = []
        if g.get("texto"):
            ctx.append(f"[Genie — texto]\n{g['texto']}")
        if g.get("colunas"):
            ctx.append(f"[Genie — dados] colunas={g['colunas']} linhas={g['linhas'][:15]}")
        for x in s.get("docs") or []:
            ctx.append(f"[{x['arquivo']}, p. {x['pagina']} — {x['secao']}]\n{x['trecho'][:2500]}")
        msgs = [{"role": "system", "content": d.agente_prompt},
                {"role": "user", "content": (f"### Histórico\n{hist}\n\n" if hist else "")
                 + "### Contexto\n" + ("\n\n".join(ctx) or "Sem contexto adicional.")
                 + f"\n\n### Pergunta\n{pergunta}" + (f"\n(Pergunta autônoma: {q})" if q != pergunta else "")}]
        try:
            resposta = d.gateway_chat(msgs, max_tokens=900)
        except d.PolicyBlock as pb:
            _passo("resp", f"Resposta barrada pela service policy '{pb.info.get('name')}' ({pb.info.get('phase')}) 🛡️ — {pb.info.get('reason') or ''}", "block")
            return {"final": {"resposta": "Não posso responder isso: a resposta foi barrada pela política de segurança do AI Gateway. "
                                          "Reformule a pergunta ou fale com um especialista Fundalis.",
                              "bloqueado": True, "assunto": s["guard"]["assunto"], "ferramentas": ["Guardrail"]}}
        except Exception as e:  # noqa: BLE001
            _passo("resp", "Falha ao gerar a resposta", "skip")
            return {"final": {"resposta": f"Ops, algo falhou ao gerar a resposta: {str(e)[:200]}", "ferramentas": s.get("usadas") or []}}
        _passo("resp", "Resposta redigida", "done")
        return {"resposta": resposta}

    def guardrail_saida(s):
        _passo("guard_out", "Guardrail de saída (PII · concorrência · vazamento de prompt)", "run")
        ok, resposta, motivo = d.guardrail_saida(s["pergunta"], s["resposta"])
        _passo("guard_out", "Guardrail de saída ok" if ok else f"Resposta ajustada pelo guardrail 🛡️ ({motivo})",
               "done" if ok else "block")
        out = {"resposta": resposta, "cards": s.get("cards") or [], "fontes": s.get("fontes") or [],
               "ferramentas": s.get("usadas") or [], "sql": s.get("sql"), "modelo": d.agent_service,
               "assunto": s["guard"]["assunto"]}
        if ok and s.get("emb") is not None:
            try:
                d.cache_grava(s["q"], s["emb"], s["escopo"], out, s["guard"]["assunto"])
            except Exception as e:  # noqa: BLE001
                d.log.warning("grava cache: %s", e)
        return {"resposta": resposta, "final": {**out, "genie_conv": s.get("genie_conv"), "cache": {"hit": False}}}

    def grava_memoria(s):
        d.hist_grava(s["conv_id"], "assistant", s["resposta"], {"assunto": s["guard"]["assunto"], "fontes": s.get("fontes") or []})
        return {}

    # roteadores
    def apos_guardrail(s):
        return "cache_semantico" if s["guard"]["permitido"] else "bloqueio"

    def apos_cache(s):
        return "resposta_cache" if s.get("final") else ["genie", "rag"]

    def apos_sintese(s):
        return END if s.get("final") else "guardrail_saida"

    g = StateGraph(Estado)
    for f in (carrega_memoria, guardrail_entrada, bloqueio, cache_semantico, resposta_cache, genie, rag,
              sintese, guardrail_saida, grava_memoria):
        g.add_node(f.__name__, no(f))
    g.add_edge(START, "carrega_memoria")
    g.add_edge("carrega_memoria", "guardrail_entrada")
    g.add_conditional_edges("guardrail_entrada", apos_guardrail, ["bloqueio", "cache_semantico"])
    g.add_edge("bloqueio", END)
    g.add_conditional_edges("cache_semantico", apos_cache, ["resposta_cache", "genie", "rag"])
    g.add_edge("resposta_cache", END)
    g.add_edge(["genie", "rag"], "sintese")
    g.add_conditional_edges("sintese", apos_sintese, ["guardrail_saida", END])
    g.add_edge("guardrail_saida", "grava_memoria")
    g.add_edge("grava_memoria", END)
    return g.compile()
