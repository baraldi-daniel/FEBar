CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS cadastro;
CREATE SCHEMA IF NOT EXISTS agente;
CREATE TABLE IF NOT EXISTS cadastro.leads (
  lead_id         text PRIMARY KEY,
  cliente_nome    text NOT NULL,
  email           text,
  telefone        text,
  documento       text,
  empresa         text,
  segmento        text,
  produto_nome    text,
  cidade          text,
  uf              text,
  regiao          text,
  canal           text,
  status          text DEFAULT 'Novo',
  mensagem        text,
  classificacao_ia text,
  score_ia        int,
  sentimento_ia   text,
  resumo_ia       text,
  proxima_acao_ia text,
  data_contato    timestamptz DEFAULT now(),
  enriquecido_em  timestamptz,
  criado_por      text,
  atualizado_em   timestamptz DEFAULT now()
);
