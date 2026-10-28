"""PDFs FICTÍCIOS de cadastro (ficha cadastral e RFQ) p/ testar o cadastro via PDF."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gera_pdfs as g  # reaproveita estilos/rodapé (e regera os PDFs base, idempotente)
g.OUT = os.path.expanduser("~/Downloads/fundalis-ia/pdfs/cadastro")
g.doc("ficha_cadastral_motores_aurora.pdf", "Ficha Cadastral de Cliente — Motores Aurora (fictícia)", [
 ("h", "Dados da empresa"),
 ("t", [["Campo", "Valor"], ["Razão social", "Motores Aurora Indústria Ltda. (fictícia)"], ["CNPJ", "45.118.302/0001-00"],
        ["Cidade/UF", "Caxias do Sul / RS"], ["Segmento", "Comercial & Caminhões"], ["Origem do contato", "Feira/Evento — Fenatran"]], [150, 330]),
 ("h", "Contato responsável"),
 ("t", [["Campo", "Valor"], ["Nome", "Ricardo Albuquerque Tavares"], ["Cargo", "Gerente de Compras Estratégicas"],
        ["E-mail", "ricardo.tavares@motoresaurora.example"], ["Telefone", "(00) 99812-4410"]], [150, 330]),
 ("h", "Necessidade"),
 "A Motores Aurora (fictícia) busca fornecedor de blocos de motor diesel em ferro vermicular (CGI) para a nova família de motores de 13 litros. Volume estimado de 6.000 peças por ano a partir do 2º semestre, com PPAP nível 3 e entrega JIT na planta de Caxias do Sul. Pede proposta técnica e comercial em até 30 dias.",
])
g.doc("rfq_grupo_horizonte.pdf", "RFQ 2026-114 — Grupo Horizonte Máquinas (fictício)", [
 ("h", "Solicitante"),
 "Grupo Horizonte Máquinas Agrícolas S.A. (fictício) — CNPJ 08.552.917/0001-01 — Rondonópolis/MT. Contato: Juliana Mendes Rocha, engenheira de suprimentos, juliana.rocha@horizonte.example, telefone (00) 98431-2207.",
 ("h", "Escopo da cotação"),
 ("t", [["Item", "Peça", "Material", "Volume anual"], ["1", "Carcaça de diferencial", "Nodular GJS-450", "2.400 un"], ["2", "Cubo de roda usinado", "Nodular GJS-600", "4.800 un"]], [40, 170, 140, 110]),
 ("h", "Condições"),
 "Entrega FCA, pagamento 60 dias, garantia mínima de 12 meses. A empresa está comparando três fornecedores e decide até o fim do trimestre. Prioridade: prazo de amostra inferior a 12 semanas.",
])
