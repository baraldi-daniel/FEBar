CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS cadastro;
CREATE SCHEMA IF NOT EXISTS agente;
CREATE TABLE IF NOT EXISTS cadastro.leads (
  lead_id text PRIMARY KEY, cliente_nome text NOT NULL, email text, telefone text, documento text, empresa text,
  segmento text, produto_nome text, cidade text, uf text, regiao text, canal text, status text DEFAULT 'Novo', mensagem text,
  classificacao_ia text, score_ia int, sentimento_ia text, resumo_ia text, proxima_acao_ia text,
  data_contato timestamptz DEFAULT now(), enriquecido_em timestamptz, criado_por text, atualizado_em timestamptz DEFAULT now());
ALTER TABLE cadastro.leads REPLICA IDENTITY FULL;
CREATE TABLE IF NOT EXISTS cadastro.lead_anexos (
  anexo_id bigserial PRIMARY KEY, lead_id text NOT NULL REFERENCES cadastro.leads(lead_id) ON DELETE CASCADE,
  arquivo text NOT NULL, path text NOT NULL, tamanho int, tipo text, origem text, criado_por text, criado_em timestamptz DEFAULT now());
ALTER TABLE cadastro.lead_anexos REPLICA IDENTITY FULL;
CREATE INDEX IF NOT EXISTS lead_anexos_lead ON cadastro.lead_anexos (lead_id);
CREATE TABLE IF NOT EXISTS agente.doc_chunks (
  chunk_id text PRIMARY KEY, arquivo text NOT NULL, pagina int, secao text, trecho text NOT NULL,
  embedding vector(1024) NOT NULL, criado_em timestamptz DEFAULT now());
CREATE INDEX IF NOT EXISTS doc_chunks_hnsw ON agente.doc_chunks USING hnsw (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS agente.llm_cache (
  id bigserial PRIMARY KEY, pergunta text NOT NULL, escopo text NOT NULL, embedding vector(1024) NOT NULL, resposta jsonb NOT NULL,
  assunto text, modelo text, hits int DEFAULT 0, criado_em timestamptz DEFAULT now(), ultimo_hit timestamptz);
CREATE INDEX IF NOT EXISTS llm_cache_hnsw ON agente.llm_cache USING hnsw (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS agente.conversas (
  id bigserial PRIMARY KEY, conv_id text NOT NULL, usuario text, papel text NOT NULL, texto text NOT NULL, meta jsonb, criado_em timestamptz DEFAULT now());
CREATE INDEX IF NOT EXISTS conversas_conv ON agente.conversas (conv_id, criado_em);
CREATE TABLE IF NOT EXISTS agente.prompts (
  versao bigserial PRIMARY KEY, nome text NOT NULL, modo text NOT NULL, modelo text NOT NULL, prompt text NOT NULL, nota text,
  ativo boolean NOT NULL DEFAULT false, criado_por text, criado_em timestamptz DEFAULT now(), atualizado_por text, atualizado_em timestamptz);
CREATE INDEX IF NOT EXISTS prompts_nome ON agente.prompts (nome, versao DESC);
CREATE UNIQUE INDEX IF NOT EXISTS prompts_um_ativo ON agente.prompts (nome) WHERE ativo;
