# Como o Fundalis IA foi construído — uso de IA no processo

Este documento descreve **o fluxo de trabalho do build**: quem fez o quê, como a ferramenta de IA foi usada, como o
resultado foi verificado e onde ela errou. As decisões técnicas do produto estão no [README](README.md); as provas de
execução estão em [`evidencias/`](evidencias/README.md).

## Ferramenta e divisão de papéis

- **Ferramenta:** Claude Code (agente de IA da Anthropic, modelo Claude Opus) rodando no terminal, com acesso a:
  shell (Databricks CLI, SDK Python, `curl`), leitura/edição de arquivos, um Chrome automatizado (Chrome DevTools)
  para pré-visualizar telas e tirar screenshots, e busca na documentação pública da Databricks.
- **Pessoa (responsável pelo projeto):** definiu os requisitos em linguagem natural, revisou as telas (enviando
  screenshots do app), pediu ajustes de UX, tomou as decisões de arquitetura e de governança e aprovou toda exclusão de
  recursos.
- **IA:** escreveu todo o código (backend FastAPI, front React/htm sem build, SQL, notebook de ML, agente LangGraph,
  `bootstrap.py`, scripts de evidência), criou os recursos no workspace pela CLI/APIs, fez os deploys, testou cada
  mudança contra o app publicado e diagnosticou falhas pelos logs.

## Método de trabalho

1. **Pedido em linguagem natural** (ex.: "o agente deve ter guardrails no prompt usando Opus 4.8", "o Lakebase deve
   sincronizar com o Unity Catalog por CDC com dados mascarados", "quero SHAP para explicabilidade").
2. **Implementação pela IA** no repositório local.
3. **Deploy** no Databricks Apps (`databricks sync` + `apps deploy`).
4. **Verificação** — sempre contra o app publicado: chamadas às APIs do próprio app (as mesmas da interface), consultas
   SQL de conferência, logs do app e, para mudanças visuais, screenshots no Chrome automatizado (prévia local com um
   proxy que serve o front local e repassa `/api` ao app publicado).
5. **Correção** quando o teste falhava, e só então o resumo para a pessoa.
6. **Memória entre sessões:** a IA mantém notas persistentes (fora do repositório) sobre apps anteriores; foi assim que o
   ponto de partida — um app semelhante feito antes para outro cliente — foi localizado e recriado neste workspace.

## Linha do tempo do build

| fase | pedido da pessoa | o que a IA fez |
|---|---|---|
| 1 | Recriar um app anterior num workspace novo, com guardrails no prompt (Opus 4.8), Lakebase como memória (cache + RAG), `ai_parse_document`, cadastro no Lakebase com CDC mascarado no UC, Genie sobre tabelas e PDFs e perguntas da inference table classificadas por assunto | Criou catálogo/schemas, Lakebase (pgvector/HNSW), CDC, views com máscara, model service no AI Gateway com inference table, Genie space, app com OBO; testou cada peça |
| 2 | Todos os dados fictícios, inclusive os PDFs | Gerou dados e PDFs sintéticos (e-mails `.example`, DDD `00`, CNPJ com dígito inválido) |
| 3 | Versão desktop; aba de documentos; CRUD de cadastro a partir de PDF; prompt de extração editável e versionado | Implementou as abas, o versionamento do prompt no Lakebase e o drag-and-drop |
| 4 | Criar logo do zero, descaracterizar a marca original e usar só o catálogo `dadosapp` | Criou a empresa fictícia **Fundalis** (logo SVG próprio), migrou tudo para `dadosapp` e, com aprovação, apagou os recursos antigos |
| 5 | Tudo visível numa tela, com rolagem só dentro de cada bloco; nova ordem das abas | Refez o layout ("tela única") e validou em duas resoluções |
| 6 | Rechupe com modelo real servido, um texto padrão completo, parâmetros editáveis, botão "Prever", SHAP e explicação em texto | Retreinou o modelo com SHAP dentro do pyfunc servido, ligou o endpoint à nova versão e trocou as regras fixas por explicabilidade |
| 7 | Guardrail em vermelho; service policies no AI Gateway; código do agente e Mermaid com LangGraph | Reescreveu o agente como `StateGraph` LangGraph (`app/agente.py`), exibiu o Mermaid gerado pelo grafo e preparou o app para bloqueios de policy |
| 8 | Evidências explícitas da execução, do modelo e das consultas | Escreveu e rodou `scripts/evidencias*.py` contra o app publicado |
| 9 | Recriar tudo num workspace novo só preenchendo um arquivo | Escreveu `config.example.env` + `bootstrap.py` idempotente e o testou do zero numa cópia separada (log em `evidencias/`) |

## Problemas encontrados nos testes e corrigidos

A maior parte do valor da IA veio de testar e diagnosticar, não só de gerar código. Exemplos reais deste build:

- **CDC parado** — a tabela no Postgres precisava de `REPLICA IDENTITY FULL`; corrigido no DDL.
- **CDC quebrado pela máscara** — column mask direto na tabela de CDC fazia o writer falhar; a máscara foi para views dinâmicas.
- **Build do Model Serving falhando** — `pandas` pinado sem wheel para Python 3.12; passou a pinar só `scikit-learn`/`cloudpickle`.
- **Kernel morto no treino** — `pip install shap` subiu o numpy para 2.x; numpy pinado na versão do runtime.
- **RAG e cache desligados de repente** — o workspace passou a bloquear chamadas diretas aos endpoints pay-per-token;
  a IA achou a causa nos logs e moveu embeddings e modelos para o AI Gateway (mesmos 1024 dims, vetores preservados).
- **Explicação SHAP cortada no meio** — limite de tokens baixo; corrigido e coberto pelo relatório de evidências.
- **Evidência travada** — `system.query.history` tinha ~1 h de atraso; a coleta passou a usar a Query History API.
- **Bootstrap** — o id do banco na API do Lakebase é `databricks-postgres` (hífen), não `databricks_postgres`;
  achado no primeiro teste do zero e corrigido.
- **Guardrail com falso positivo** ("Qual fundição teve maior refugo?" bloqueada) — regra e exemplos no prompt.
- **Cache que não reaproveitava paráfrases** — limiar ajustado e trava para números diferentes ("8 mil" ≠ "30 mil").

## Limites e erros da IA (registrados com honestidade)

- **Service policies do AI Gateway:** a IA não conseguiu criá-las — a documentação diz que a criação é só pela UI, e a
  API pública responde "SERVICE policies is currently disabled in UC". Ela deixou os prompts prontos e o app preparado
  para tratar o bloqueio; criar a policy é passo manual.
- **Suposição corrigida:** no início a IA concluiu que não havia policy de guardrail no AI Gateway e implementou o
  guardrail só como prompt no Opus 4.8; a pessoa mostrou a aba *Policies* (Beta) na UI e o app foi ajustado.
- **Prévia local confundida com o app:** a pessoa usou a janela de prévia da IA (Chrome automatizado), que já tinha sido
  desligada, e viu "failed to fetch"; a IA explicou e passou a fechar a prévia após cada teste.
- **Identidade nas chamadas ao modelo:** o token do usuário repassado ao app não tem o escopo `ai-gateway`, então a
  inference table registra o service principal como `requester`; consultas a dados (Genie, SQL) rodam como o usuário.

## Governança do uso de IA no build

- Nenhuma credencial foi gravada em arquivo: autenticação sempre pelo perfil do Databricks CLI; tokens só em memória.
- Uma concessão ampla (`GRANT … TO account users`) foi **bloqueada pelo classificador de permissões** do ambiente da
  IA; as permissões ficaram restritas ao service principal do app e a decisão de abrir acesso ficou com a pessoa.
- Exclusões de recursos (app anterior, catálogo antigo, cópias de teste) só foram feitas após confirmação explícita, e
  sempre com listagem prévia do que seria apagado.
- E-mails e ids de service principal foram removidos dos arquivos de evidência antes da publicação.
