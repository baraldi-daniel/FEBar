CREATE OR REPLACE VIEW dadosapp.fundalis_ia.leads COMMENT 'Leads/clientes cadastrados no Lakebase (cadastro.leads), replicados por CDC e com PII mascarada (LGPD) — estado atual. Dados FICTÍCIOS.' AS
WITH h AS (SELECT *, row_number() OVER (PARTITION BY lead_id ORDER BY _pg_lsn DESC, _sort_by DESC) AS rn FROM dadosapp.fundalis_cdc.lb_leads_history WHERE _pg_change_type <> 'update_preimage')
SELECT lead_id, dadosapp.fundalis_ia.mask_nome(cliente_nome) AS cliente_nome, dadosapp.fundalis_ia.mask_email(email) AS email, dadosapp.fundalis_ia.mask_tel(telefone) AS telefone, dadosapp.fundalis_ia.mask_doc(documento) AS documento,
  empresa, segmento, produto_nome, cidade, uf, regiao, canal, status, mensagem, classificacao_ia, score_ia, sentimento_ia,
  dadosapp.fundalis_ia.mask_texto(resumo_ia, cliente_nome) AS resumo_ia, dadosapp.fundalis_ia.mask_texto(proxima_acao_ia, cliente_nome) AS proxima_acao_ia,
  CAST(data_contato AS TIMESTAMP) AS data_contato, CAST(enriquecido_em AS TIMESTAMP) AS enriquecido_em, criado_por,
  CAST(atualizado_em AS TIMESTAMP) AS atualizado_em, CAST(_timestamp AS TIMESTAMP) AS sincronizado_em
FROM h WHERE rn = 1 AND _pg_change_type <> 'delete';;
CREATE OR REPLACE VIEW dadosapp.fundalis_ia.leads_anexos COMMENT 'Anexos dos leads (Lakebase → CDC). Arquivos no Volume fundalis_ia.anexos. Dados FICTÍCIOS.' AS
WITH h AS (SELECT *, row_number() OVER (PARTITION BY anexo_id ORDER BY _pg_lsn DESC, _sort_by DESC) rn FROM dadosapp.fundalis_cdc.lb_lead_anexos_history WHERE _pg_change_type <> 'update_preimage')
SELECT anexo_id, lead_id, arquivo, tamanho, tipo, origem, criado_por, CAST(criado_em AS TIMESTAMP) criado_em FROM h WHERE rn = 1 AND _pg_change_type <> 'delete';;
CREATE OR REPLACE FUNCTION dadosapp.fundalis_ia.buscar_documentos(pergunta STRING COMMENT 'Pergunta ou termos a procurar nos documentos') RETURNS TABLE (arquivo STRING, pagina INT, secao STRING, trecho STRING, relevancia DOUBLE) COMMENT 'Busca semântica nos documentos FICTÍCIOS da Fundalis processados com ai_parse_document (catálogo técnico, manual de qualidade, política comercial, relatório de operações).' RETURN SELECT arquivo, pagina, secao, trecho, ai_similarity(trecho, pergunta) AS relevancia FROM dadosapp.fundalis_ia.documentos_chunks ORDER BY relevancia DESC LIMIT 4
