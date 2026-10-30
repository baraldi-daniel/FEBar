# Evidências de execução

Tudo nesta pasta é **saída real** de execuções contra o workspace Databricks (não são exemplos escritos à mão).
Cada relatório `.md` tem ao lado o JSON bruto da mesma execução e é regenerável pelo script indicado.
E-mails e ids de service principal foram substituídos por `<usuário>` / `<service-principal-do-app>`.
Todos os dados são fictícios.

| arquivo | o que comprova | gerado por |
|---|---|---|
| [`bootstrap_execucao.log`](bootstrap_execucao.log) | **o build roda do zero**: saída completa do `bootstrap.py` criando tudo num conjunto novo de recursos (catálogo/schemas, Lakebase, CDC, model service + inference table, treino e serving do modelo, Genie, app, deploy, documentos) e o smoke test final (painel, agente, guardrail, rechupe) | `python3 bootstrap.py --config <config>` |
| [`EVIDENCIAS.md`](EVIDENCIAS.md) · [`evidencias.json`](evidencias.json) | o app publicado funcionando: 12 perguntas ao agente com os passos do grafo, fontes e SQL do Genie; cache semântico (hit numa paráfrase, miss com número diferente); 4 bloqueios de guardrail; rechupe com SHAP; cadastro por PDF → Lakebase → CDC → UC mascarado; documentos; assuntos da inference table | `scripts/evidencias.py` |
| [`QUERIES.md`](QUERIES.md) · [`queries.json`](queries.json) | as consultas do agente rastreadas **fora do app**: mensagem e SQL pela API do Genie, statement no Query History do warehouse **executado pelo usuário** (OBO), chamadas registradas na inference table do AI Gateway e no Lakebase (histórico, trechos do RAG, plano com índice HNSW) | `scripts/evidencias_queries.py` |
| [`../notebooks/10_rechupe_model_execucao.ipynb`](../notebooks/10_rechupe_model_execucao.ipynb) | **notebook com as saídas das células** da execução real do job que treinou a v2 do modelo: taxa de rechupe 0,416 em 9.000 linhas sintéticas, AUC 0,901 e relatório de classificação no teste, importância SHAP, registro da versão 2 no Unity Catalog e checagem da aditividade do SHAP | export da execução do job (`/api/2.1/jobs/runs/export`) |
| [`RECHUPE.md`](RECHUPE.md) · [`rechupe.json`](rechupe.json) | o modelo de ML: registro no UC e run do MLflow (AUC de teste 0,901), endpoint servindo a v2, dataset sintético, avaliação escorando o endpoint (AUC, acurácia, Brier, calibração), aditividade do SHAP, curvas de sensibilidade e casos em texto livre | `scripts/evidencias_rechupe.py` |

Como o build foi feito (uso de IA no processo): [`../COMO_FOI_CONSTRUIDO.md`](../COMO_FOI_CONSTRUIDO.md).
