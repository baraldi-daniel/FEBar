"""Evidências das CONSULTAS feitas pelo agente: cada pergunta é rastreada em fontes independentes do app —
Genie API (conversa/mensagem/SQL), system.query.history (statement executado no warehouse e POR QUEM — prova do OBO),
inference table do AI Gateway (chamadas ao Opus 4.8) e Lakebase (histórico, cache, trechos do RAG, plano HNSW).
Gera evidencias/QUERIES.md e evidencias/queries.json.

Uso:  APP_URL=... DATABRICKS_CONFIG_PROFILE=... WAREHOUSE_ID=... LAKEBASE_HOST=... LAKEBASE_USER=... APP_SP_CLIENT_ID=... \\
      python3 scripts/evidencias_queries.py"""
import datetime, json, os, re, subprocess, time, urllib.error, urllib.request, uuid
import psycopg
from databricks.sdk import WorkspaceClient

APP = os.environ["APP_URL"].rstrip("/")
PERFIL = os.environ["DATABRICKS_CONFIG_PROFILE"]
WH = os.environ["WAREHOUSE_ID"]
SP = os.getenv("APP_SP_CLIENT_ID", "")
INFER = os.getenv("APP_INFERENCE_TABLE", "dadosapp.fundalis_ia.fundalis_agente_payload")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "evidencias")
w = WorkspaceClient(profile=PERFIL)
TOKEN = json.loads(subprocess.check_output(["databricks", "auth", "token", "-p", PERFIL]))["access_token"]


def sql(q):
    r = w.statement_execution.execute_statement(warehouse_id=WH, statement=q, wait_timeout="50s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error.message)
    cols = [c.name for c in r.manifest.schema.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])]


def app(metodo, caminho, corpo=None, timeout=400):
    r = urllib.request.Request(APP + caminho, data=json.dumps(corpo).encode() if corpo is not None else None, method=metodo,
                               headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    return urllib.request.urlopen(r, timeout=timeout).read().decode()


def chat(pergunta, tentativas=3):
    import http.client
    for t in range(tentativas):
        try:
            final = {}
            for l in app("POST", "/api/chat/stream", {"pergunta": pergunta, "conv_id": str(uuid.uuid4()), "usar_cache": False}).splitlines():
                if l.strip():
                    o = json.loads(l)
                    if o["tipo"] == "final":
                        final = o
            if final:
                return final
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError) as e:
            print(f"  falha transitória ({type(e).__name__}), tentando de novo…")
        time.sleep(5)
    return {}


def pg():
    tok = json.loads(subprocess.check_output(["databricks", "postgres", "generate-database-credential",
                                              os.environ["LAKEBASE_ENDPOINT"],
                                              "-p", PERFIL, "-o", "json"]))["token"]
    return psycopg.connect(host=os.environ["LAKEBASE_HOST"], dbname="databricks_postgres", user=os.environ["LAKEBASE_USER"],
                           password=tok, sslmode="require", autocommit=True)


def pg_rows(c, q, p=None):
    with c.cursor() as cur:
        cur.execute(q, p)
        if cur.description is None:          # comandos sem resultado (SET, etc.)
            return []
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def esperar(fn, ok, tentativas=30, pausa=20, rotulo=""):
    for i in range(tentativas):
        r = fn()
        if ok(r):
            return r
        print(f"  aguardando {rotulo} ({i + 1})…")
        time.sleep(pausa)
    return fn()


def main():
    ev = {"inicio": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    t0 = ev["inicio"].replace("+00:00", "")
    # 0) o que o Genie enxerga (configuração do space)
    sid = None
    perguntas = ["Quais os 5 produtos que mais vendem?",
                 "Qual a receita por canal de venda?",
                 "Quantos leads quentes temos por segmento?",
                 "Quais foram os 5 leads cadastrados mais recentemente e de quais empresas?",
                 "Qual o desconto para 8 mil peças por ano?"]
    ev["chat"] = []
    for p in perguntas:
        print("chat:", p)
        f = chat(p)
        ev["chat"].append({"pergunta": p, "resposta": f.get("resposta"), "ferramentas": f.get("ferramentas"), "sql_app": f.get("sql"),
                           "genie": f.get("genie"), "fontes": f.get("fontes"), "conv_id": f.get("conv_id"), "ms": f.get("ms")})
        sid = sid or (f.get("genie") or {}).get("space_id")
    # 1) Genie API: lê de volta cada mensagem (com o token do próprio usuário)
    for c in ev["chat"]:
        g = c.get("genie") or {}
        if not g.get("message_id"):
            continue
        m = w.api_client.do("GET", f"/api/2.0/genie/spaces/{g['space_id']}/conversations/{g['conversation_id']}/messages/{g['message_id']}")
        q = next((a["query"] for a in m.get("attachments") or [] if a.get("query")), {})
        c["genie_api"] = {"status": m.get("status"), "conteudo": m.get("content"), "descricao": q.get("description"),
                          "sql": q.get("query"), "statement_id": q.get("statement_id"),
                          "linhas": (q.get("query_result_metadata") or {}).get("row_count")}
    if sid:
        sp = w.api_client.do("GET", f"/api/2.0/genie/spaces/{sid}", query={"include_serialized_space": "true"})
        ser = json.loads(sp.get("serialized_space") or "{}")
        ev["genie_space"] = {"space_id": sid, "titulo": sp.get("title"), "warehouse_id": sp.get("warehouse_id"),
                             "tabelas": [t.get("identifier") for t in (ser.get("data_sources") or {}).get("tables", [])],
                             "funcoes": [f.get("identifier") for f in (ser.get("instructions") or {}).get("sql_functions", [])]}
    # 2) Painel/lista de leads (SQL OBO do app) — gera statements p/ conferir o executed_by
    app("GET", "/api/leads?limit=5")
    app("GET", "/api/cadastro/recentes?limit=5")
    # 3) system.query.history: statements do Genie (por statement_id) + do app no período
    ids = [x for x in ((c.get("genie_api") or {}).get("statement_id") or (c.get("genie") or {}).get("statement_id") for c in ev["chat"]) if x]
    # Query History API (/api/2.0/sql/history/queries) — quase em tempo real; system.query.history tem ~1 h de atraso
    def hist(filtro):
        out, tok = [], None
        while True:
            body = {"filter_by": filtro, "max_results": 100, "include_metrics": True}
            if tok:
                body = {"page_token": tok, "max_results": 100, "include_metrics": True}
            r = w.api_client.do("GET", "/api/2.0/sql/history/queries", body=body)
            out += r.get("res") or []
            tok = r.get("next_page_token") if r.get("has_next_page") else None
            if not tok:
                return out

    def resumo(q):
        m = q.get("metrics") or {}
        return {"statement_id": q.get("query_id"), "executed_by": q.get("user_name"), "executed_as": q.get("executed_as_user_name"),
                "warehouse": q.get("warehouse_id"), "status": q.get("status"), "duracao_ms": q.get("duration"),
                "linhas": m.get("rows_produced_count"), "origem": (q.get("query_source") or {}) or q.get("client_application"),
                "inicio_ms": q.get("query_start_time_ms"), "statement_text": q.get("query_text")}

    ev["query_history_genie"] = esperar(lambda: [resumo(q) for q in hist({"statement_ids": ids})] if ids else [],
                                        lambda r: len(r) >= len(ids), tentativas=10, pausa=15, rotulo="Query History API (Genie)")
    ini_ms = int(datetime.datetime.fromisoformat(ev["inicio"]).timestamp() * 1000)
    todas = [resumo(q) for q in hist({"warehouse_ids": [WH], "query_start_time_range": {"start_time_ms": ini_ms}})]
    grupos = {}
    for q in todas:
        if q["statement_id"] in ids or "fundalis_ia" not in (q["statement_text"] or ""):
            continue
        g = grupos.setdefault(q["executed_by"], {"executed_by": q["executed_by"], "client_application": "Databricks App", "n": 0, "exemplos": []})
        g["n"] += 1
        t = re.sub(r"\s+", " ", q["statement_text"] or "")[:90]
        if t not in g["exemplos"] and len(g["exemplos"]) < 4:
            g["exemplos"].append(t)
    ev["query_history_app"] = sorted(grupos.values(), key=lambda g: -g["n"])
    # system.query.history (tabela de sistema): melhor esforço — só aparece quando o atraso da tabela já passou
    try:
        lista = ", ".join(f"'{x}'" for x in ids) or "''"
        ev["system_query_history"] = sql(f"""SELECT statement_id, executed_by, client_application, execution_status
                                             FROM system.query.history WHERE start_time >= '{t0}' AND statement_id IN ({lista})""")
    except Exception as e:  # noqa: BLE001
        ev["system_query_history"] = {"erro": str(e)[:200]}
    # 4) inference table do AI Gateway: chamadas do agente no período
    qi = f"""SELECT CAST(event_time AS STRING) t, requester, status_code, latency_ms, destination_model,
                    CASE WHEN request LIKE '%FUNDALIS-GUARDRAIL-ENTRADA%' THEN 'guardrail_entrada'
                         WHEN request LIKE '%FUNDALIS-GUARDRAIL-SAIDA%' THEN 'guardrail_saida'
                         WHEN request LIKE '%FUNDALIS-AGENTE%' THEN 'sintese' ELSE 'outra' END etapa,
                    regexp_extract(request, 'PERGUNTA DO USU[^<]*<<<([^>]{{1,140}})', 1) pergunta_guardrail,
                    regexp_extract(get_json_object(response, '$.choices[0].message.content'), '"assunto"[^"]*"([^"]+)"', 1) assunto
             FROM {INFER} WHERE event_time >= '{t0}' ORDER BY event_time"""
    ev["inference_table"] = esperar(lambda: sql(qi), lambda r: sum(1 for x in r if x["etapa"] == "sintese") >= len(perguntas),
                                    tentativas=15, rotulo="inference table")
    # 5) Lakebase: histórico das conversas, trechos usados no RAG, índice HNSW e plano da busca vetorial
    with pg() as c:
        convs = [x["conv_id"] for x in ev["chat"] if x.get("conv_id")]
        ev["lakebase_conversas"] = pg_rows(c, """SELECT conv_id, papel, left(texto, 120) conteudo, criado_em::text
                                                  FROM agente.conversas WHERE conv_id = ANY(%s) ORDER BY criado_em""", (convs,))
        chunks = sorted({f["chunk_id"] for x in ev["chat"] for f in (x.get("fontes") or []) if f.get("chunk_id")})
        ev["lakebase_chunks"] = pg_rows(c, "SELECT chunk_id, arquivo, pagina, secao, left(trecho, 90) trecho FROM agente.doc_chunks WHERE chunk_id = ANY(%s) ORDER BY chunk_id", (chunks,))
        ev["lakebase_indices"] = pg_rows(c, "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'agente' AND indexdef ILIKE '%hnsw%'")
        pg_rows(c, "SET enable_seqscan = off")   # tabela pequena: força o planner a mostrar o caminho pelo índice HNSW
        ev["lakebase_plano_rag"] = [r["QUERY PLAN"] for r in pg_rows(c, """EXPLAIN SELECT chunk_id FROM agente.doc_chunks
            ORDER BY embedding <=> (SELECT embedding FROM agente.doc_chunks LIMIT 1) LIMIT 6""")]
        ev["lakebase_cache"] = pg_rows(c, "SELECT count(*) entradas, coalesce(sum(hits),0) hits, count(DISTINCT escopo) escopos FROM agente.llm_cache")
    ev["fim"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    s = json.dumps(ev, ensure_ascii=False, default=str)
    s = re.sub(r"[\w.+-]+@databricks\.com", "<usuário>", s)
    if SP:
        s = s.replace(SP, "<service-principal-do-app>")
    ev = json.loads(s)
    json.dump(ev, open(os.path.join(SAIDA, "queries.json"), "w"), ensure_ascii=False, indent=2)
    open(os.path.join(SAIDA, "QUERIES.md"), "w").write(relatorio(ev))
    print("ok →", SAIDA)


def desc(t):
    """Texto extraído do JSON bruto da inference table pode vir com escapes \\uXXXX."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t or "")


def cel(v, n=160):
    t = re.sub(r"\s+", " ", str(v if v is not None else "—")).replace("|", "/").strip()
    return t if len(t) <= n else t[:n - 1] + "…"


def relatorio(ev):
    L = ["# Evidências — consultas do agente (Genie, warehouse, AI Gateway, Lakebase)", "",
         f"Execução de {ev['inicio']} a {ev['fim']} (UTC) contra o app publicado. Cada pergunta foi feita ao agente pelo app e depois "
         "**rastreada em fontes independentes do app**: a API do Genie, o Query History do SQL warehouse, a inference "
         "table do AI Gateway e o próprio Lakebase. JSON bruto: [`queries.json`](queries.json). Gerado por `scripts/evidencias_queries.py`. "
         "Todos os dados são fictícios.", ""]
    gs = ev.get("genie_space") or {}
    L += ["## 1. O que o Genie enxerga", "", f"Space `{gs.get('space_id')}` — {gs.get('titulo')} · warehouse `{gs.get('warehouse_id')}`", "",
          "- Tabelas: " + ", ".join(f"`{t}`" for t in gs.get("tabelas") or []),
          "- Funções SQL: " + (", ".join(f"`{f}`" for f in gs.get("funcoes") or []) or "—"), ""]
    hist = {h["statement_id"]: h for h in ev["query_history_genie"]}
    L += ["## 2. Pergunta → Genie → statement no warehouse", ""]
    for i, c in enumerate(ev["chat"], 1):
        g, ga = c.get("genie") or {}, c.get("genie_api") or {}
        h = hist.get(ga.get("statement_id") or g.get("statement_id")) or {}
        L += [f"### 2.{i} {c['pergunta']}", "",
              f"> {cel(c['resposta'], 600)}", "",
              f"Ferramentas do agente: {', '.join(c.get('ferramentas') or [])} · {round((c.get('ms') or 0) / 1000, 1)} s", ""]
        if not g.get("message_id"):
            L += ["O guardrail de entrada marcou esta pergunta como de **documentos** (não precisa de dados tabulares), então o "
                  "agente **não acionou o Genie**: a resposta veio só do RAG no Lakebase (trechos abaixo).", ""]
            if c.get("fontes"):
                L += ["Trechos usados do RAG (Lakebase): " + ", ".join(f"`{f['chunk_id']}` ({f['similaridade']:.2f})" for f in c["fontes"]), ""]
            continue
        L += [
              "| evidência | valor |", "|---|---|",
              f"| Genie — conversa / mensagem | `{g.get('conversation_id')}` / `{g.get('message_id')}` |",
              f"| Genie API — status da mensagem | {ga.get('status')} |",
              f"| Genie API — descrição da consulta | {cel(ga.get('descricao'), 300)} |",
              f"| statement_id | `{ga.get('statement_id') or g.get('statement_id')}` |",
              f"| Query History — executado por / como | **{h.get('executed_by', 'não encontrado')}** / {h.get('executed_as')} |",
              f"| Query History — warehouse / origem | `{h.get('warehouse')}` / {cel(h.get('origem'), 120)} |",
              f"| Query History — status / duração / linhas | {h.get('status')} / {h.get('duracao_ms')} ms / {h.get('linhas')} |",
              "", "SQL que o Genie gerou e o warehouse executou (texto do statement no Query History):", "", "```sql",
              (h.get("statement_text") or ga.get("sql") or c.get("sql_app") or "").strip(), "```", ""]
        if c.get("fontes"):
            L += ["Trechos usados do RAG (Lakebase): " + ", ".join(f"`{f['chunk_id']}` ({f['similaridade']:.2f})" for f in c["fontes"]), ""]
    L += ["## 3. Outras consultas SQL do app no mesmo período (Query History do warehouse)", "",
          "Consultas do Painel/Cadastro rodam **on-behalf-of** (executadas pelo usuário); as internas do app (sincronização da "
          "inference table, lista de documentos) rodam como o service principal.", "",
          "| executado por | origem | statements | exemplos |", "|---|---|---|---|"]
    L += [f"| {r['executed_by']} | {r['client_application']} | {r['n']} | {cel('; '.join(r['exemplos']), 260)} |" for r in ev["query_history_app"]]
    sq = ev.get("system_query_history")
    L += ["", "Conferência na tabela de sistema `system.query.history` (tem ~1 h de atraso): "
          + (f"{len(sq)} dos {len(hist)} statements do Genie já presentes." if isinstance(sq, list) else f"indisponível ({sq})")]
    L += ["", "## 4. Chamadas ao modelo registradas na inference table do AI Gateway", "",
          f"`{INFER}` (model service do agente, Opus 4.8). Cada pergunta gera 3 chamadas: "
          "guardrail de entrada (que também classifica o assunto), síntese da resposta e guardrail de saída.", "",
          "| horário (UTC) | etapa | pergunta (guardrail) | assunto | requester | status | latência |", "|---|---|---|---|---|---|---|"]
    L += [f"| {r['t'][11:19]} | {r['etapa']} | {cel(desc(r['pergunta_guardrail']), 70) if r['pergunta_guardrail'] else ''} | {desc(r['assunto'] or '')} | "
          f"{r['requester']} | {r['status_code']} | {r['latency_ms']} ms |" for r in ev["inference_table"]]
    L += ["", "O `requester` aparece como o service principal porque o token do usuário repassado ao app não tem o escopo "
          "`ai-gateway`; as consultas a dados (Genie e SQL) é que rodam com a identidade do usuário (seções 2 e 3).", "",
          "## 5. Lakebase — memória do agente", "",
          "Histórico das conversas desta execução (`agente.conversas`):", "", "| conversa | papel | conteúdo | quando |", "|---|---|---|---|"]
    L += [f"| `{r['conv_id'][:8]}…` | {r['papel']} | {cel(r['conteudo'], 120)} | {r['criado_em'][:19]} |" for r in ev["lakebase_conversas"]]
    L += ["", "Trechos recuperados pela busca vetorial (`agente.doc_chunks`):", "", "| chunk | arquivo | pág. | seção |", "|---|---|---|---|"]
    L += [f"| `{r['chunk_id']}` | {r['arquivo']} | {r['pagina']} | {cel(r['secao'], 80)} |" for r in ev["lakebase_chunks"]]
    L += ["", "Índices HNSW (pgvector):", ""] + [f"- `{r['indexname']}` em `{r['tablename']}`: `{r['indexdef']}`" for r in ev["lakebase_indices"]]
    L += ["", "Plano da busca vetorial do RAG (`ORDER BY embedding <=> :q LIMIT 6`):", "", "```"] + ev["lakebase_plano_rag"] + ["```", ""]
    cc = (ev.get("lakebase_cache") or [{}])[0]
    L += [f"Cache semântico (`agente.llm_cache`): {cc.get('entradas')} entradas · {cc.get('hits')} hits · {cc.get('escopos')} escopo(s) de PII.", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import sys
    if "--so-relatorio" in sys.argv:          # regenera o QUERIES.md a partir do queries.json já coletado
        open(os.path.join(SAIDA, "QUERIES.md"), "w").write(relatorio(json.load(open(os.path.join(SAIDA, "queries.json")))))
    else:
        main()
