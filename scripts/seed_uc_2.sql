CREATE OR REPLACE TABLE dadosapp.fundalis_ia.representantes COMMENT 'Representantes comerciais FICTÍCIOS (demo)' AS
WITH base AS (SELECT id, rand(11) a, rand(12) b, rand(13) c FROM (SELECT explode(sequence(1,24)) AS id))
SELECT concat('REP-', lpad(cast(id as string),4,'0')) AS representante_id,
  concat(element_at(array('Ana','Bruno','Carla','Diego','Eduarda','Felipe','Gabriela','Henrique','Isabela','João','Karina','Lucas','Marina','Nelson','Olívia','Paulo'), cast(a*16 as int)+1),
         ' ', element_at(array('Menezes','Andreatta','Bevilaqua','Zanatta','Fontana','Maggi','Nishimura','Bueno','Alves','Ferreira'), cast(b*10 as int)+1)) AS nome,
  element_at(array('Sul','Sudeste','Exportação','Sul','Sudeste'), cast(a*5 as int)+1) AS regional,
  element_at(array('Powertrain','Estruturais','Usinagem','Novos Negócios'), cast(c*4 as int)+1) AS equipe,
  round(2000000 + b*18000000, 0) AS meta_receita
FROM base;;
CREATE OR REPLACE TABLE dadosapp.fundalis_ia.vendas COMMENT 'Vendas FICTÍCIAS de peças fundidas/usinadas (demo). cliente_nome é PII mascarada.' AS
WITH base AS (SELECT id, rand(21) a, rand(22) b, rand(23) c, rand(24) d, rand(25) e, rand(26) f, rand(27) g, rand(28) h,
                     rand(29) i, rand(30) j, rand(31) k, rand(32) m, rand(33) n
              FROM (SELECT explode(sequence(1,4000)) AS id)),
pick AS (SELECT base.*, element_at(array(0,1,2,7,8,9,10,4,5,0,1,7,8,9,3,6,11,13,16,17), cast(a*20 as int)+1) AS prn FROM base),
prd AS (SELECT produto_id, nome, familia, marca, preco, row_number() OVER (ORDER BY produto_id)-1 AS rn FROM dadosapp.fundalis_ia.produtos),
uni AS (SELECT unidade_id, nome, row_number() OVER (ORDER BY unidade_id)-1 AS rn, count(*) OVER () AS tot FROM dadosapp.fundalis_ia.unidades),
rep AS (SELECT representante_id, nome, regional, row_number() OVER (ORDER BY representante_id)-1 AS rn, count(*) OVER () AS tot FROM dadosapp.fundalis_ia.representantes)
SELECT venda_id, produto_id, produto_nome, familia, marca, unidade_id, unidade_nome,
  representante_id, representante_nome, regional, cliente_nome, empresa, segmento, canal,
  element_at(array('Londrina','Uberlândia','São Paulo','Betim','Curitiba','Caxias do Sul','Sorocaba','São Bernardo do Campo','Contagem','Extrema','Canoas','Gravataí','Campinas','Jundiaí','São José dos Pinhais','Diadema','Porto Alegre','São Carlos'), cast(rcity*18 as int)+1) AS cidade,
  element_at(array('SC','SP','SP','MG','PR','RS','SP','SP','MG','MG','RS','RS','SP','SP','PR','SP','RS','SP'), cast(rcity*18 as int)+1) AS uf,
  element_at(array('Sul','Sudeste','Sudeste','Sudeste','Sul','Sul','Sudeste','Sudeste','Sudeste','Sudeste','Sul','Sul','Sudeste','Sudeste','Sul','Sudeste','Sul','Sudeste'), cast(rcity*18 as int)+1) AS regiao,
  volume,
  round(volume * preco * (0.9 + rval*0.25), -2) AS valor,
  element_at(array('À vista','Prazo 30 dias','Prazo 60 dias','Boleto','Contrato de fornecimento'), cast(rfp*5 as int)+1) AS forma_pagamento,
  data_venda
FROM (
  SELECT concat('VEN-', lpad(cast(pick.id as string),6,'0')) AS venda_id,
    p.produto_id, p.nome AS produto_nome, p.familia, p.marca,
    u.unidade_id, u.nome AS unidade_nome,
    r.representante_id, r.nome AS representante_nome, r.regional,
    concat(element_at(array('João','Marcos','Luiz','Sebastião','Antônio','Carlos','Rodrigo','Paulo','Cláudio','Fernando','Ricardo','Eduardo','Roberto','Gustavo','Vicente','Nelson','Adriano','Wilson','Maria','Fernanda'), cast(pick.g*20 as int)+1),
           ' ', element_at(array('Alves','Souza','Menezes','Ferreira','Oliveira','Fontana','Maggi','Bueno','Zanatta','Nishimura','Schneider','Pivetta','Dalpiaz','Marchesan','Rossi','Costa','Scheffer','Bertaso','Moretto','Griebeler'), cast(pick.h*20 as int)+1)) AS cliente_nome,
    element_at(array('Automotivo Leve','Comercial & Caminhões','Off-Road & Agrícola','Industrial','Hidrogênio & Energia','Automotivo Leve'), cast(pick.j*6 as int)+1) AS segmento,
    element_at(array('Exportação','OEM Nacional','Exportação','Aftermarket','Novos Negócios'), cast(pick.n*5 as int)+1) AS canal,
    element_at(array('Powertrain Alfa (fictícia)','Motores Atlântico (fictícia)','Máquinas Serra Azul (fictícia)','Metalúrgica Horizonte (fictícia)','Energia H2 Sul (fictícia)','Montadora Aurora (fictícia)'), cast(pick.j*6 as int)+1) AS empresa,
    greatest(1, round(1 + pow(pick.b,3) * (CASE p.familia WHEN 'Componentes Estruturais' THEN 500 WHEN 'Cubos & Carcaças' THEN 400 WHEN 'Coletores & Múltiplos' THEN 350 WHEN 'Peças Usinadas' THEN 300 WHEN 'Cabeçotes' THEN 250 ELSE 200 END), 0)) AS volume,
    p.preco AS preco, pick.e AS rval, pick.m AS rcity, pick.i AS rfp,
    cast(current_timestamp() - make_interval(0,0,0, cast(pick.f*365 as int),0,0,0) AS timestamp) AS data_venda
  FROM pick
  JOIN prd p ON p.rn = pick.prn
  JOIN uni u ON u.rn = cast(pick.c*u.tot as int) % u.tot
  JOIN rep r ON r.rn = cast(pick.d*r.tot as int) % r.tot
) v;;
CREATE VOLUME IF NOT EXISTS dadosapp.fundalis_ia.docs COMMENT 'PDFs FICTÍCIOS enviados ao agente (processados com ai_parse_document)'
