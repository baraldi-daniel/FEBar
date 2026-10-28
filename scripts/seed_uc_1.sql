CREATE OR REPLACE TABLE dadosapp.fundalis_ia.produtos (produto_id string, nome string, familia string, marca string, emoji string, unidade string, preco double, descricao string) COMMENT 'Catálogo FICTÍCIO de peças fundidas e usinadas da Fundalis (demo)';;
INSERT INTO dadosapp.fundalis_ia.produtos VALUES
("PRD-01","Bloco de Motor Diesel CGI","Blocos de Motor","Ferro Vermicular (CGI)","⚙️","peça",3200.0,"Bloco de motor diesel em ferro vermicular (CGI); alta resistência mecânica e menor peso para altas pressões de combustão."),
("PRD-02","Bloco de Motor Flex","Blocos de Motor","Ferro Cinzento","⚙️","peça",1450.0,"Bloco de motor flex em ferro cinzento para veículos leves; boa usinabilidade e amortecimento de vibração."),
("PRD-03","Bloco V8 Diesel","Blocos de Motor","Ferro Vermicular (CGI)","⚙️","peça",3600.0,"Bloco V8 diesel em CGI para linha pesada e off-road; rigidez estrutural elevada."),
("PRD-04","Bloco Agrícola Off-Road","Blocos de Motor","Ferro Cinzento","⚙️","peça",2100.0,"Bloco para motores agrícolas e off-road; durabilidade em regime severo de trabalho."),
("PRD-05","Cabeçote Diesel Pesado","Cabeçotes","Ferro Vermicular (CGI)","🔧","peça",1350.0,"Cabeçote diesel pesado em CGI; resiste a altas pressões e cargas térmicas de combustão."),
("PRD-06","Cabeçote Comercial","Cabeçotes","Ferro Nodular","🔧","peça",980.0,"Cabeçote para veículos comerciais em ferro nodular; resistência à fadiga."),
("PRD-07","Cabeçote Flex","Cabeçotes","Ferro Cinzento","🔧","peça",720.0,"Cabeçote flex para automóveis leves; boa condução térmica."),
("PRD-08","Braço de Controle","Componentes Estruturais","Ferro Nodular","🛠️","peça",320.0,"Braço de controle de suspensão em ferro nodular; tenacidade e absorção de carga."),
("PRD-09","Suporte de Motor","Componentes Estruturais","Ferro Nodular","🛠️","peça",240.0,"Suporte de motor em nodular; alta resistência à fadiga e amortecimento."),
("PRD-10","Componente de Suspensão","Componentes Estruturais","Ferro Nodular","🛠️","peça",380.0,"Componente estrutural de suspensão para linha comercial e off-road."),
("PRD-11","Cubo de Roda","Cubos & Carcaças","Ferro Nodular","🛠️","peça",290.0,"Cubo de roda em ferro nodular; peça de segurança com precisão dimensional."),
("PRD-12","Carcaça de Diferencial","Cubos & Carcaças","Ferro Nodular","🛠️","peça",680.0,"Carcaça de diferencial para eixos comerciais; parede espessa e integridade interna."),
("PRD-13","Carcaça de Turbina","Cubos & Carcaças","Ferro Nodular","🏭","peça",540.0,"Carcaça de turbina em nodular resistente a altas temperaturas."),
("PRD-14","Coletor de Escape","Coletores & Múltiplos","Ferro Nodular","🏭","peça",420.0,"Coletor de escape em nodular austemperado (SiMo); resistência a choque térmico."),
("PRD-15","Múltiplo de Admissão","Coletores & Múltiplos","Ferro Cinzento","🏭","peça",300.0,"Múltiplo de admissão em ferro cinzento; geometria complexa."),
("PRD-16","Virabrequim Usinado","Peças Usinadas","Usinado","🔩","peça",1900.0,"Virabrequim com usinagem de precisão; balanceamento e tolerâncias apertadas."),
("PRD-17","Disco de Freio","Peças Usinadas","Ferro Cinzento","🔩","peça",180.0,"Disco de freio ventilado em ferro cinzento; grafita e dureza controladas p/ dissipação."),
("PRD-18","Cubo Usinado Completo","Peças Usinadas","Usinado","🔩","peça",460.0,"Cubo de roda com usinagem completa e furação pronta para montagem.");;
CREATE OR REPLACE TABLE dadosapp.fundalis_ia.unidades (unidade_id string, nome string, cidade string, uf string, regiao string, tipo string) COMMENT 'Unidades fabris FICTÍCIAS (demo)';;
INSERT INTO dadosapp.fundalis_ia.unidades VALUES
("UN-01","Matriz Ponta Grossa","Ponta Grossa","PR","Sul","Matriz"),
("UN-02","Fundição Ponta Grossa I","Ponta Grossa","PR","Sul","Fundição"),
("UN-03","Fundição Ponta Grossa II","Ponta Grossa","PR","Sul","Fundição"),
("UN-04","Usinagem Ponta Grossa","Ponta Grossa","PR","Sul","Usinagem"),
("UN-05","Fundição Limeira","Limeira","SP","Sudeste","Fundição"),
("UN-06","Usinagem Limeira","Limeira","SP","Sudeste","Usinagem"),
("UN-07","Centro Técnico Ponta Grossa","Ponta Grossa","PR","Sul","Centro Técnico"),
("UN-08","Fundição Divinópolis","Divinópolis","MG","Sudeste","Fundição"),
("UN-09","Usinagem Sete Lagoas","Sete Lagoas","MG","Sudeste","Usinagem"),
("UN-10","Fundição Itajaí","Itajaí","SC","Sul","Fundição"),
("UN-11","Fundição Santa Maria","Santa Maria","RS","Sul","Fundição"),
("UN-12","Usinagem Rio Claro","Rio Claro","SP","Sudeste","Usinagem");;
CREATE OR REPLACE TABLE dadosapp.fundalis_ia.culturas (cultura_id string, nome string, categoria string, emoji string, problemas_comuns string, descricao string) COMMENT 'Tipos de peça × defeitos típicos (referência da inspeção por foto)';;
INSERT INTO dadosapp.fundalis_ia.culturas VALUES
("CUL-01","Bloco de Motor","Powertrain","⚙️","rechupe (contração), porosidade por gás, trinca a quente, macho deslocado","Peça mais complexa; núcleos internos e paredes finas exigem controle de solidificação."),
("CUL-02","Cabeçote","Powertrain","🔧","porosidade, rechupe em pontos quentes, trinca, inclusão de escória","Alta densidade de machos e câmaras; sensível a gases e pontos quentes."),
("CUL-03","Virabrequim","Powertrain","⚙️","trinca, inclusão, segregação, dupla pele","Requer alta resistência à fadiga; controle metalúrgico rígido."),
("CUL-04","Cubo de Roda","Estrutural","🛠️","porosidade, rechupe, inclusão, dureza fora de faixa","Peça de segurança; exige integridade interna e precisão dimensional."),
("CUL-05","Carcaça de Diferencial","Estrutural","🛠️","rechupe, porosidade, falta de enchimento, distorção","Peça de parede espessa; propensa a rechupe interno."),
("CUL-06","Coletor de Escape","Powertrain","🏭","trinca térmica, oxidação, porosidade, dupla pele","Sujeito a choque térmico; produzido em nodular austemperado (SiMo)."),
("CUL-07","Disco de Freio","Freios","🛑","porosidade, inclusão, dureza irregular, empeno","Ferro cinzento; grafita e dureza controladas para atrito e dissipação."),
("CUL-08","Componente Estrutural","Estrutural","🛠️","rechupe, porosidade, trinca a frio, inclusão","Peças de suspensão/chassi em nodular; tenacidade é crítica.")