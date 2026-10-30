import json, os, uuid
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"])
FQ = os.getenv("APP_FQ", "dadosapp.fundalis_ia")          # catálogo.schema dos dados do app
T = os.getenv("GENIE_TITLE", "Fundalis IA — Vendas, Leads & Documentos")
i = lambda: uuid.uuid4().hex
tabs = {
 f"{FQ}.vendas": "Vendas FICTÍCIAS de peças fundidas/usinadas (produto, unidade, representante, canal, segmento, UF, valor em R$, volume em peças, data). cliente_nome é PII mascarada.",
 f"{FQ}.produtos": "Catálogo de produtos (família, material na coluna marca, preço de tabela).",
 f"{FQ}.unidades": "Unidades fabris (fundição, usinagem, matriz, centro técnico).",
 f"{FQ}.representantes": "Representantes comerciais e metas de receita.",
 f"{FQ}.culturas": "Tipos de peça e defeitos de fundição mais comuns.",
 f"{FQ}.leads": "Leads/clientes cadastrados pelo app no Lakebase e replicados por CDC. Nome, e-mail, telefone e documento são MASCARADOS (LGPD) para quem não tem acesso.",
 f"{FQ}.documentos_chunks": "Trechos (por seção) dos PDFs da empresa extraídos com ai_parse_document: catálogo técnico, manual de qualidade/defeitos, política comercial e relatório de operações.",
 f"{FQ}.perguntas_classificadas": "Perguntas feitas ao agente (extraídas da inference table do AI Gateway) com o assunto classificado pelo guardrail do Opus 4.8.",
}
instr = f"""Você responde sobre a Fundalis (fundição de ferro). TODOS os dados são fictícios.
- Receita = SUM(vendas.valor) em R$; mostre em milhões (R$ mi) quando for grande. Volume = SUM(vendas.volume) em peças.
- 'Exportação' é o canal = 'Exportação'. Funil de leads = leads.status (Novo, Em contato, Cotação, Proposta, Fechado, Perdido).
- Leads quentes: leads.classificacao_ia = 'Quente' (score_ia >= 70).
- NUNCA tente desmascarar ou inferir dados pessoais; colunas mascaradas devem ser exibidas como estão.
- Para perguntas sobre CONTEÚDO DOS DOCUMENTOS (política comercial, descontos, prazos, garantia, critérios de qualidade,
  defeitos, especificações técnicas, indicadores das unidades no relatório), use a função {FQ}.buscar_documentos(pergunta)
  ou filtre {FQ}.documentos_chunks por palavras-chave (ILIKE) e responda citando arquivo e seção.
- Não compare a Fundalis com concorrentes."""
ex = [
 ("Qual a receita por família de produto nos últimos 90 dias?",
  f"SELECT familia, ROUND(SUM(valor)/1e6, 2) AS receita_mi FROM {FQ}.vendas WHERE data_venda >= current_date() - INTERVAL 90 DAYS GROUP BY familia ORDER BY receita_mi DESC"),
 ("Qual o desconto por volume anual na política comercial?",
  f"SELECT arquivo, secao, trecho FROM {FQ}.buscar_documentos('desconto por volume anual')"),
 ("Quantos leads quentes temos por segmento?",
  f"SELECT segmento, COUNT(*) AS leads_quentes FROM {FQ}.leads WHERE classificacao_ia = 'Quente' GROUP BY segmento ORDER BY leads_quentes DESC"),
]
space = {"version": 2,
 "config": {"sample_questions": [{"id": i(), "question": [q]} for q in [
   "Qual a receita por família nos últimos 90 dias?", "Quantos leads quentes por segmento?",
   "Qual o refugo de cada fundição no relatório do 3T26?", "Qual o critério de aceitação de porosidade para peças classe B?",
   "Quais assuntos mais perguntados ao agente hoje?"]]},
 "data_sources": {"tables": [{"identifier": t, "description": [d]} for t, d in sorted(tabs.items())]},
 "instructions": {"text_instructions": [{"id": i(), "content": [instr]}],
                  "example_question_sqls": sorted([{"id": i(), "question": [q], "sql": [s]} for q, s in ex], key=lambda x: x["id"]),
                  "sql_functions": [{"id": i(), "identifier": f"{FQ}.buscar_documentos"}]}}
ex_sp = [s for s in (w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces") or []) if s.get("title") == T]
body = {"title": T, "description": "Vendas, leads (mascarados) e documentos PDF da Fundalis — dados fictícios.",
        "warehouse_id": os.environ["WAREHOUSE_ID"], "serialized_space": json.dumps(space, ensure_ascii=False)}
if ex_sp:
    sid = ex_sp[0]["space_id"]; w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{sid}", body=body)
else:
    sid = w.api_client.do("POST", "/api/2.0/genie/spaces", body=body)["space_id"]
print(sid)
