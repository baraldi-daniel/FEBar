CREATE TABLE IF NOT EXISTS agente.doc_chunks (
  chunk_id   text PRIMARY KEY,
  arquivo    text NOT NULL,
  pagina     int,
  secao      text,
  trecho     text NOT NULL,
  embedding  vector(1024) NOT NULL,
  criado_em  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS doc_chunks_hnsw ON agente.doc_chunks USING hnsw (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS agente.llm_cache (
  id           bigserial PRIMARY KEY,
  pergunta     text NOT NULL,
  escopo       text NOT NULL,           -- 'pii' | 'mascarado' (resposta depende do acesso a PII)
  embedding    vector(1024) NOT NULL,
  resposta     jsonb NOT NULL,
  assunto      text,
  modelo       text,
  hits         int DEFAULT 0,
  criado_em    timestamptz DEFAULT now(),
  ultimo_hit   timestamptz
);
CREATE INDEX IF NOT EXISTS llm_cache_hnsw ON agente.llm_cache USING hnsw (embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS agente.conversas (
  id         bigserial PRIMARY KEY,
  conv_id    text NOT NULL,
  usuario    text,
  papel      text NOT NULL,            -- 'user' | 'assistant'
  texto      text NOT NULL,
  meta       jsonb,
  criado_em  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversas_conv ON agente.conversas (conv_id, criado_em);
