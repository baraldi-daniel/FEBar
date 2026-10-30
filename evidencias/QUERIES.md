# Evidências — consultas do agente (Genie, warehouse, AI Gateway, Lakebase)

Execução de 2026-10-29T17:57:45+00:00 a 2026-10-29T18:00:13+00:00 (UTC) contra o app publicado. Cada pergunta foi feita ao agente pelo app e depois **rastreada em fontes independentes do app**: a API do Genie, o Query History do SQL warehouse, a inference table do AI Gateway e o próprio Lakebase. JSON bruto: [`queries.json`](queries.json). Gerado por `scripts/evidencias_queries.py`. Todos os dados são fictícios.

## 1. O que o Genie enxerga

Space `01f1d243ce9b112085a163448f7fc129` — Fundalis IA — Vendas, Leads & Documentos · warehouse `76ebfd04694394df`

- Tabelas: `dadosapp.fundalis_ia.culturas`, `dadosapp.fundalis_ia.documentos_chunks`, `dadosapp.fundalis_ia.leads`, `dadosapp.fundalis_ia.perguntas_classificadas`, `dadosapp.fundalis_ia.produtos`, `dadosapp.fundalis_ia.representantes`, `dadosapp.fundalis_ia.unidades`, `dadosapp.fundalis_ia.vendas`
- Funções SQL: `dadosapp.fundalis_ia.buscar_documentos`

## 2. Pergunta → Genie → statement no warehouse

### 2.1 Quais os 5 produtos que mais vendem?

> Os 5 produtos com maior volume de vendas na Fundalis são: 1. **Componente de Suspensão** — 53.042 peças (R$ 20,7 mi) 2. **Suporte de Motor** — 52.360 peças (R$ 12,8 mi) 3. **Braço de Controle** — 50.576 peças (R$ 16,6 mi) 4. **Bloco de Motor Diesel CGI** — 22.376 peças (R$ 73,4 mi) 5. **Cubo de Roda** — 21.168 peças (R$ 6,3 mi) O Componente de Suspensão lidera em volume, mas o Bloco de Motor Diesel CGI se destaca pela maior receita, mesmo com volume menor. Posso detalhar algum deles?

Ferramentas do agente: Genie, Documentos (RAG) · 31.5 s

| evidência | valor |
|---|---|
| Genie — conversa / mensagem | `01f1d3c241591daa9338282e33e55f88` / `01f1d3c241711f88ae3d8748908c8cf0` |
| Genie API — status da mensagem | COMPLETED |
| Genie API — descrição da consulta | Você quer ver os 5 produtos que tiveram o maior volume total de vendas na Fundalis, mostrando também o volume total vendido e a receita total gerada por esses produtos. |
| statement_id | `01f1d3c2-48f4-1e03-a61e-ad4af6a9cd24` |
| Query History — executado por / como | **<usuário>** / <usuário> |
| Query History — warehouse / origem | `76ebfd04694394df` / {'genie_space_id': '01f1d243ce9b112085a163448f7fc129'} |
| Query History — status / duração / linhas | FINISHED / 679 ms / 5 |

SQL que o Genie gerou e o warehouse executou (texto do statement no Query History):

```sql
WITH `produtos_ranked` AS (
  SELECT
    `produto_nome`,
    SUM(`volume`) AS `volume_total`,
    SUM(`valor`) AS `receita_total`,
    RANK() OVER (ORDER BY SUM(`volume`) DESC) AS `rank_volume`
  FROM `dadosapp`.`fundalis_ia`.`vendas`
  WHERE `produto_nome` IS NOT NULL
    AND `volume` IS NOT NULL
  GROUP BY `produto_nome`
)
SELECT
  `produto_nome`,
  `volume_total`,
  `receita_total`
FROM `produtos_ranked`
WHERE `rank_volume` <= 5
ORDER BY `rank_volume`, `produto_nome`
```

Trechos usados do RAG (Lakebase): `catalogo_tecnico_2026.pdf#002` (0.45), `catalogo_tecnico_2026.pdf#001` (0.40), `politica_comercial_2026.pdf#001` (0.40), `manual_qualidade_defeitos.pdf#001` (0.39), `relatorio_operacoes_3t26.pdf#001` (0.39)

### 2.2 Qual a receita por canal de venda?

> Aqui está a receita por canal de venda: - **Exportação:** R$ 110,4 mi - **Novos Negócios:** R$ 59,2 mi - **Aftermarket:** R$ 55,6 mi - **OEM Nacional:** R$ 53,4 mi A **Exportação** lidera a receita, enquanto o **OEM Nacional** tem o menor valor. Posso ajudar com mais alguma análise?

Ferramentas do agente: Genie · 22.4 s

| evidência | valor |
|---|---|
| Genie — conversa / mensagem | `01f1d3c253fd136b85818c3077e7094e` / `01f1d3c2540912d4bbfe1af7b426dbdc` |
| Genie API — status da mensagem | COMPLETED |
| Genie API — descrição da consulta | Você quer ver a receita total gerada por cada canal de venda. |
| statement_id | `01f1d3c2-5751-1b32-8d9b-74a05d283363` |
| Query History — executado por / como | **<usuário>** / <usuário> |
| Query History — warehouse / origem | `76ebfd04694394df` / {'genie_space_id': '01f1d243ce9b112085a163448f7fc129'} |
| Query History — status / duração / linhas | FINISHED / 311 ms / 4 |

SQL que o Genie gerou e o warehouse executou (texto do statement no Query History):

```sql
SELECT `canal`, SUM(`valor`) AS `receita`
FROM `dadosapp`.`fundalis_ia`.`vendas`
WHERE `canal` IS NOT NULL
GROUP BY `canal`
ORDER BY `receita` DESC
```

### 2.3 Quantos leads quentes temos por segmento?

> Aqui estão os leads quentes por segmento: - **Hidrogênio & Energia:** 44 - **Automotivo Leve:** 42 - **Off-Road & Agrícola:** 41 - **Comercial & Caminhões:** 41 - **Industrial:** 37 No total são 5 segmentos, com Hidrogênio & Energia na liderança e Industrial com o menor volume. Posso ajudar com mais algum detalhe?

Ferramentas do agente: Genie · 22.9 s

| evidência | valor |
|---|---|
| Genie — conversa / mensagem | `01f1d3c261e414478bdee4b368996bee` / `01f1d3c261fa161b901735c23533578b` |
| Genie API — status da mensagem | COMPLETED |
| Genie API — descrição da consulta | Você quer saber quantos leads classificados como 'Quente' existem em cada segmento, mostrando a contagem de leads quentes por segmento e ordenando do segmento com mais leads para o com menos. |
| statement_id | `01f1d3c2-63f8-1b9d-a415-bdae7b28ce18` |
| Query History — executado por / como | **<usuário>** / <usuário> |
| Query History — warehouse / origem | `76ebfd04694394df` / {'genie_space_id': '01f1d243ce9b112085a163448f7fc129'} |
| Query History — status / duração / linhas | FINISHED / 427 ms / 5 |

SQL que o Genie gerou e o warehouse executou (texto do statement no Query History):

```sql
SELECT `segmento`, COUNT(*) AS `leads_quentes`
FROM `dadosapp`.`fundalis_ia`.`leads`
WHERE `classificacao_ia` = 'Quente'
  AND `segmento` IS NOT NULL
GROUP BY `segmento`
ORDER BY `leads_quentes` DESC
```

### 2.4 Quais foram os 5 leads cadastrados mais recentemente e de quais empresas?

> Aqui estão os 5 leads mais recentes (todos de 27/10/2026): 1. **LEAD-000305** — W************* — Grupo Forge (fictícia) — 18:15 2. **LEAD-000348** — F*************** — Indústria Atlântico (fictícia) — 16:15 3. **LEAD-000321** — L*************** — Grupo Powertrain (fictícia) — 15:15 4. **LEAD-000122** — P************* — Cliente Forge (fictícia) — 14:15 5. **LEAD-000033** — M************* — Indústria Forge (fictícia) — 07:15 Posso ajudar com mais algum detalhe?

Ferramentas do agente: Genie, Documentos (RAG) · 25.7 s

| evidência | valor |
|---|---|
| Genie — conversa / mensagem | `01f1d3c2706c138182affd90cb099b25` / `01f1d3c2707c1fb0912c0a6b56416053` |
| Genie API — status da mensagem | COMPLETED |
| Genie API — descrição da consulta | Você quer ver os 5 leads cadastrados mais recentemente, incluindo o nome do cliente, a empresa e a data do contato. |
| statement_id | `01f1d3c2-7527-187a-9c69-9839587969d0` |
| Query History — executado por / como | **<usuário>** / <usuário> |
| Query History — warehouse / origem | `76ebfd04694394df` / {'genie_space_id': '01f1d243ce9b112085a163448f7fc129'} |
| Query History — status / duração / linhas | FINISHED / 921 ms / 5 |

SQL que o Genie gerou e o warehouse executou (texto do statement no Query History):

```sql
WITH ranked_leads AS (
  SELECT
    `lead_id`,
    `cliente_nome`,
    `empresa`,
    `data_contato`,
    ROW_NUMBER() OVER (ORDER BY `data_contato` DESC) AS rn
  FROM `dadosapp`.`fundalis_ia`.`leads`
  WHERE `data_contato` IS NOT NULL
)
SELECT
  `lead_id`,
  `cliente_nome`,
  `empresa`,
  `data_contato`
FROM ranked_leads
WHERE rn <= 5
ORDER BY `data_contato` DESC;
```

Trechos usados do RAG (Lakebase): `catalogo_tecnico_2026.pdf#003` (0.35)

### 2.5 Qual o desconto para 8 mil peças por ano?

> Para 8.000 peças/ano, o desconto é de **6% sobre a tabela**, exigindo contrato anual [politica_comercial_2026.pdf, p. 1].

Ferramentas do agente: Documentos (RAG) · 4.9 s

O guardrail de entrada marcou esta pergunta como de **documentos** (não precisa de dados tabulares), então o agente **não acionou o Genie**: a resposta veio só do RAG no Lakebase (trechos abaixo).

Trechos usados do RAG (Lakebase): `politica_comercial_2026.pdf#003` (0.65), `politica_comercial_2026.pdf#002` (0.38)

## 3. Outras consultas SQL do app no mesmo período (Query History do warehouse)

Consultas do Painel/Cadastro rodam **on-behalf-of** (executadas pelo usuário); as internas do app (sincronização da inference table, lista de documentos) rodam como o service principal.

| executado por | origem | statements | exemplos |
|---|---|---|---|
| <usuário> | Databricks App | 15 | SELECT lead_id, cliente_nome, email, telefone, documento, empresa, segmento, produto_nome,; SELECT lead_id, cliente_nome, empresa, produto_nome, segmento, cidade, uf, canal, status,; SELECT `dadosapp`.`fundalis_ia`.pii_liberado() AS l; DESCRIBE WITH ranked_le… |

Conferência na tabela de sistema `system.query.history` (tem ~1 h de atraso): 0 dos 4 statements do Genie já presentes.

## 4. Chamadas ao modelo registradas na inference table do AI Gateway

`dadosapp.fundalis_ia.fundalis_agente_payload` (model service do agente, Opus 4.8). Cada pergunta gera 3 chamadas: guardrail de entrada (que também classifica o assunto), síntese da resposta e guardrail de saída.

| horário (UTC) | etapa | pergunta (guardrail) | assunto | requester | status | latência |
|---|---|---|---|---|---|---|
| 17:57:46 | guardrail_entrada | Quais os 5 produtos que mais vendem? | Vendas & Receita | <service-principal-do-app> | 200 | 1608 ms |
| 17:58:13 | sintese |  |  | <service-principal-do-app> | 200 | 3130 ms |
| 17:58:16 | guardrail_saida |  |  | <service-principal-do-app> | 200 | 1497 ms |
| 17:58:18 | guardrail_entrada | Qual a receita por canal de venda? | Vendas & Receita | <service-principal-do-app> | 200 | 1819 ms |
| 17:58:38 | sintese |  |  | <service-principal-do-app> | 200 | 1840 ms |
| 17:58:39 | guardrail_saida |  |  | <service-principal-do-app> | 200 | 1133 ms |
| 17:58:41 | guardrail_entrada | Quantos leads quentes temos por segmento? | Leads & Clientes | <service-principal-do-app> | 200 | 1534 ms |
| 17:59:01 | sintese |  |  | <service-principal-do-app> | 200 | 2154 ms |
| 17:59:03 | guardrail_saida |  |  | <service-principal-do-app> | 200 | 1289 ms |
| 17:59:05 | guardrail_entrada | Quais foram os 5 leads cadastrados mais recentemente e de quais empre… | Leads & Clientes | <service-principal-do-app> | 200 | 1948 ms |
| 17:59:27 | sintese |  |  | <service-principal-do-app> | 200 | 2674 ms |
| 17:59:29 | guardrail_saida |  |  | <service-principal-do-app> | 200 | 1336 ms |
| 17:59:32 | guardrail_entrada | Qual o desconto para 8 mil peças por ano? | Política Comercial | <service-principal-do-app> | 200 | 1476 ms |
| 17:59:34 | sintese |  |  | <service-principal-do-app> | 200 | 1248 ms |
| 17:59:35 | guardrail_saida |  |  | <service-principal-do-app> | 200 | 1455 ms |

O `requester` aparece como o service principal porque o token do usuário repassado ao app não tem o escopo `ai-gateway`; as consultas a dados (Genie e SQL) é que rodam com a identidade do usuário (seções 2 e 3).

## 5. Lakebase — memória do agente

Histórico das conversas desta execução (`agente.conversas`):

| conversa | papel | conteúdo | quando |
|---|---|---|---|
| `27f9acb0…` | user | Quais os 5 produtos que mais vendem? | 2026-10-29 17:57:46 |
| `27f9acb0…` | assistant | Os 5 produtos com maior volume de vendas na Fundalis são: 1. **Componente de Suspensão** — 53.042 peças (R$ 20,7 mi) 2. | 2026-10-29 17:58:17 |
| `f5574834…` | user | Qual a receita por canal de venda? | 2026-10-29 17:58:18 |
| `f5574834…` | assistant | Aqui está a receita por canal de venda: - **Exportação:** R$ 110,4 mi - **Novos Negócios:** R$ 59,2 mi - **Aftermarket: | 2026-10-29 17:58:41 |
| `f69a00dc…` | user | Quantos leads quentes temos por segmento? | 2026-10-29 17:58:41 |
| `f69a00dc…` | assistant | Aqui estão os leads quentes por segmento: - **Hidrogênio & Energia:** 44 - **Automotivo Leve:** 42 - **Off-Road & Agríc | 2026-10-29 17:59:04 |
| `7681f14e…` | user | Quais foram os 5 leads cadastrados mais recentemente e de quais empresas? | 2026-10-29 17:59:05 |
| `7681f14e…` | assistant | Aqui estão os 5 leads mais recentes (todos de 27/10/2026): 1. **LEAD-000305** — W************* — Grupo Forge (fictícia) | 2026-10-29 17:59:31 |
| `c811ac34…` | user | Qual o desconto para 8 mil peças por ano? | 2026-10-29 17:59:32 |
| `c811ac34…` | assistant | Para 8.000 peças/ano, o desconto é de **6% sobre a tabela**, exigindo contrato anual [politica_comercial_2026.pdf, p. 1] | 2026-10-29 17:59:37 |

Trechos recuperados pela busca vetorial (`agente.doc_chunks`):

| chunk | arquivo | pág. | seção |
|---|---|---|---|
| `catalogo_tecnico_2026.pdf#001` | catalogo_tecnico_2026.pdf | 1 | Fundalis — Catálogo Técnico de Produtos 2026 (fictício) |
| `catalogo_tecnico_2026.pdf#002` | catalogo_tecnico_2026.pdf | 1 | 1. Visão geral |
| `catalogo_tecnico_2026.pdf#003` | catalogo_tecnico_2026.pdf | 1 | 2. Especificações de referência por produto |
| `manual_qualidade_defeitos.pdf#001` | manual_qualidade_defeitos.pdf | 1 | Fundalis — Manual de Qualidade: Defeitos de Fundição e Ações Corretivas (fictíc… |
| `politica_comercial_2026.pdf#001` | politica_comercial_2026.pdf | 1 | Fundalis — Política Comercial e Condições de Fornecimento 2026 (fictício) |
| `politica_comercial_2026.pdf#002` | politica_comercial_2026.pdf | 1 | 1. Condições de pagamento |
| `politica_comercial_2026.pdf#003` | politica_comercial_2026.pdf | 1 | 2. Descontos por volume anual |
| `relatorio_operacoes_3t26.pdf#001` | relatorio_operacoes_3t26.pdf | 1 | Fundalis — Relatório Trimestral de Operações 3T26 (fictício) |

Índices HNSW (pgvector):

- `doc_chunks_hnsw` em `doc_chunks`: `CREATE INDEX doc_chunks_hnsw ON agente.doc_chunks USING hnsw (embedding vector_cosine_ops)`
- `llm_cache_hnsw` em `llm_cache`: `CREATE INDEX llm_cache_hnsw ON agente.llm_cache USING hnsw (embedding vector_cosine_ops)`

Plano da busca vetorial do RAG (`ORDER BY embedding <=> :q LIMIT 6`):

```
Limit  (cost=10000000106.08..10000000106.95 rows=6 width=40)
  InitPlan 1
    ->  Limit  (cost=10000000000.00..10000000000.03 rows=1 width=32)
          ->  Seq Scan on doc_chunks doc_chunks_1  (cost=10000000000.00..10000000014.00 rows=400 width=32)
  ->  Index Scan using doc_chunks_hnsw on doc_chunks  (cost=106.04..164.00 rows=400 width=40)
        Order By: (embedding <=> (InitPlan 1).col1)
```

Cache semântico (`agente.llm_cache`): 22 entradas · 1 hits · 1 escopo(s) de PII.

