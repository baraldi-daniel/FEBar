"""Gera PDFs FICTÍCIOS da Fundalis para a demo (todo conteúdo inventado)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
import os
OUT = os.path.expanduser("~/Downloads/fundalis-ia/pdfs")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=colors.HexColor("#0B3D91"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor("#0B3D91"))
P = ParagraphStyle("p", parent=ss["BodyText"], leading=14, spaceAfter=6)
AVISO = "DOCUMENTO FICTÍCIO — criado exclusivamente para demonstração. Números, nomes, prazos e condições são inventados."
def rodape(c, d):
    c.saveState(); c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(colors.grey)
    c.drawString(40, 25, AVISO); c.drawRightString(555, 25, f"pág. {d.page}"); c.restoreState()
def tabela(rows, widths=None):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B3D91")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8.5), ("GRID", (0,0), (-1,-1), .4, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EEF3FB")]), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    return t
def doc(nome, titulo, partes):
    d = SimpleDocTemplate(os.path.join(OUT, nome), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=45, title=titulo, author="Fundalis IA (empresa fictícia)")
    els = [Paragraph(titulo, H1), Paragraph(f"<i>{AVISO}</i>", P), Spacer(1, 8)]
    for p in partes:
        if isinstance(p, tuple) and p[0] == "h": els.append(Paragraph(p[1], H2))
        elif isinstance(p, tuple) and p[0] == "t": els.append(tabela(p[1], p[2] if len(p) > 2 else None)); els.append(Spacer(1, 8))
        elif p == "pb": els.append(PageBreak())
        else: els.append(Paragraph(p, P))
    d.build(els, onFirstPage=rodape, onLaterPages=rodape); print("gerado", nome)

doc("catalogo_tecnico_2026.pdf", "Fundalis — Catálogo Técnico de Produtos 2026 (fictício)", [
 ("h", "1. Visão geral"),
 "Este catálogo reúne as famílias de peças fundidas e usinadas oferecidas pela Fundalis em 2026: blocos de motor, cabeçotes, componentes estruturais, cubos e carcaças, coletores e peças usinadas. Todas as especificações abaixo são de referência e podem ser ajustadas ao desenho do cliente (OEM).",
 ("h", "2. Especificações de referência por produto"),
 ("t", [["Código", "Produto", "Material", "Peso (kg)", "Dureza (HB)", "Lead time", "Lote mínimo"],
        ["PRD-01", "Bloco de Motor Diesel CGI", "Ferro vermicular GJV-450", "182", "200–250", "14 semanas", "500 un"],
        ["PRD-02", "Bloco de Motor Flex", "Ferro cinzento GJL-250", "38", "180–230", "10 semanas", "2.000 un"],
        ["PRD-03", "Bloco V8 Diesel", "Ferro vermicular GJV-500", "245", "210–260", "16 semanas", "300 un"],
        ["PRD-05", "Cabeçote Diesel Pesado", "Ferro vermicular GJV-450", "96", "200–250", "12 semanas", "500 un"],
        ["PRD-06", "Cabeçote Comercial", "Ferro nodular GJS-500", "54", "170–230", "10 semanas", "800 un"],
        ["PRD-11", "Cubo de Roda", "Ferro nodular GJS-600", "12", "190–270", "8 semanas", "5.000 un"],
        ["PRD-12", "Carcaça de Diferencial", "Ferro nodular GJS-450", "41", "160–210", "9 semanas", "1.500 un"],
        ["PRD-14", "Coletor de Escape", "Nodular SiMo 4.5", "9", "200–250", "8 semanas", "3.000 un"],
        ["PRD-16", "Virabrequim Usinado", "Ferro nodular GJS-700", "28", "230–290", "12 semanas", "1.000 un"],
        ["PRD-17", "Disco de Freio", "Ferro cinzento GJL-200 alto C", "8", "170–220", "6 semanas", "10.000 un"]],
  [45, 120, 110, 50, 55, 60, 60]),
 ("h", "3. Usinagem"),
 "As unidades de usinagem (Ponta Grossa, Limeira, Sete Lagoas e Rio Claro) entregam peças com usinagem completa em centros CNC de 5 eixos, com tolerância típica de ±0,02 mm em mancais e rugosidade Ra 0,8 µm em faces de vedação. O teste de estanqueidade é 100% para blocos e cabeçotes (vazamento máximo 2 cm³/min a 2 bar).",
 ("h", "4. Embalagem e logística"),
 "Peças pesadas são expedidas em racks metálicos retornáveis (até 8 blocos por rack). Peças leves seguem em caixas plásticas KLT. Para exportação, utiliza-se embalagem VCI anticorrosiva com validade de 6 meses.",
 ("h", "5. Contato técnico (fictício)"),
 "Engenharia de Aplicação — engenharia.aplicacao@fundalis.example — telefone (00) 0000-0000. Atendimento de segunda a sexta, das 8h às 17h.",
])

doc("manual_qualidade_defeitos.pdf", "Fundalis — Manual de Qualidade: Defeitos de Fundição e Ações Corretivas (fictício)", [
 ("h", "1. Objetivo"),
 "Padronizar a identificação, a classificação e o tratamento dos principais defeitos de fundição em ferro (cinzento, nodular e vermicular), com critérios de aceitação por classe de peça.",
 ("h", "2. Rechupe (contração)"),
 "O rechupe é uma cavidade causada pela contração do metal durante a solidificação, típica de pontos quentes (seções espessas isoladas). Principais causas: massalote subdimensionado, temperatura de vazamento acima de 1.420 °C, módulo de solidificação mal distribuído e baixo carbono equivalente (CE < 4,2). Ações: redimensionar massalotes (regra do módulo 1,2× da seção alimentada), usar resfriadores (coquilhas) nos pontos quentes, ajustar CE para 4,3–4,4 e reduzir a temperatura de vazamento para 1.370–1.400 °C. Detecção: raio-X digital e ultrassom; em peças de segurança, inspeção 100%.",
 ("h", "3. Porosidade por gás"),
 "Poros esféricos e lisos provocados por gases (hidrogênio, nitrogênio) ou umidade da areia. Ações: controlar umidade da areia verde em 3,0–3,6%, permeabilidade mínima de 120, secar machos e respiros adequados. Limite de nitrogênio no banho: 90 ppm.",
 ("h", "4. Trinca a quente e trinca a frio"),
 "Trincas a quente ocorrem por restrição à contração em alta temperatura; trincas a frio surgem por tensões residuais no desmoldagem precoce. Ações: aumentar o tempo de resfriamento no molde para no mínimo 45 min em blocos, revisar raios de concordância (mínimo 3 mm) e colapsibilidade dos machos.",
 ("h", "5. Inclusão de escória e macho deslocado"),
 "Inclusões vêm de escória não removida ou erosão do molde; use filtros cerâmicos de espuma 10 ppi e bacia de vazamento com barragem. Macho deslocado: revisar marcações (prints) e usar chapelins; tolerância de deslocamento ≤ 0,5 mm.",
 ("h", "6. Critérios de aceitação por classe"),
 ("t", [["Defeito", "Classe A (segurança)", "Classe B (powertrain)", "Classe C (geral)", "Ensaio"],
        ["Rechupe interno", "Não permitido", "≤ 2 mm, fora de áreas usinadas", "≤ 4 mm", "Raio-X / US"],
        ["Porosidade", "≤ 0,5 mm isolada", "≤ 1,5 mm, máx. 3 por dm²", "≤ 3 mm", "Raio-X"],
        ["Trinca", "Não permitida", "Não permitida", "Não permitida", "Líquido penetrante"],
        ["Inclusão", "≤ 0,3 mm", "≤ 1 mm", "≤ 2 mm", "Metalografia"],
        ["Dureza fora de faixa", "Rejeita lote", "Retrabalho térmico", "Concessão", "Brinell"]],
  [90, 95, 120, 80, 95]),
 ("h", "7. Indicadores de referência (metas fictícias 2026)"),
 "Meta de refugo interno: 3,5% (blocos) e 2,0% (componentes estruturais). Meta de PPM no cliente: 25 PPM. Tempo máximo de resposta a reclamação (8D – D3, contenção): 24 horas; relatório 8D completo em 10 dias úteis.",
])

doc("politica_comercial_2026.pdf", "Fundalis — Política Comercial e Condições de Fornecimento 2026 (fictício)", [
 ("h", "1. Condições de pagamento"),
 "Prazo padrão de 60 dias fora o mês para OEMs com contrato; 30 dias para clientes de reposição (aftermarket). Pagamento antecipado tem desconto financeiro de 1,5% ao mês, pro rata.",
 ("h", "2. Descontos por volume anual"),
 ("t", [["Volume anual (peças)", "Desconto sobre tabela", "Observação"],
        ["até 1.000", "0%", "Preço de tabela"],
        ["1.001 a 5.000", "3%", "Requer previsão trimestral"],
        ["5.001 a 20.000", "6%", "Contrato anual"],
        ["acima de 20.000", "9%", "Contrato plurianual + programação firme de 8 semanas"]], [140, 120, 230]),
 ("h", "3. Reajuste por sucata e liga"),
 "Os preços são reajustados trimestralmente pela variação do índice de sucata de aço (fictício ISA-T) e do ferro-gusa: Preço novo = Preço base × (0,55 + 0,30 × ISA-T atual/ISA-T base + 0,15 × Gusa atual/Gusa base). Variações inferiores a 2% não geram reajuste.",
 ("h", "4. Amostras e desenvolvimento"),
 "Ferramental (modelos e caixas de macho) é cobrado à parte e pertence ao cliente após quitação. Prazo de amostras iniciais (PPAP nível 3): 12 a 16 semanas após o congelamento do desenho. Lote-piloto urgente pode ser antecipado em até 4 semanas mediante taxa de 8% sobre o ferramental.",
 ("h", "5. Incoterms e frete"),
 "Mercado interno: FCA planta de origem. Exportação: FCA porto de Paranaguá ou Santos; DAP sob consulta. O frete de reposição urgente é por conta do cliente.",
 ("h", "6. Garantia"),
 "Garantia de 12 meses a partir da entrega ou 24 meses a partir da montagem no veículo, o que ocorrer primeiro, limitada à substituição da peça e a custos de triagem previamente acordados.",
 ("h", "7. Política de concorrência e confidencialidade"),
 "A equipe comercial não comenta preços, clientes ou capacidade de outras fundições. Informações técnicas de clientes são tratadas sob NDA e nunca são compartilhadas entre clientes.",
])

doc("relatorio_operacoes_3t26.pdf", "Fundalis — Relatório Trimestral de Operações 3T26 (fictício)", [
 ("h", "1. Destaques do trimestre"),
 "O 3T26 (fictício) registrou volume de 182 mil toneladas fundidas, alta de 4,1% sobre o 2T26, puxada por blocos diesel CGI para a linha pesada e por componentes estruturais para off-road. A taxa de refugo consolidada caiu de 4,6% para 4,1%.",
 ("h", "2. Indicadores por unidade"),
 ("t", [["Unidade", "Capacidade (t/trim.)", "Utilização", "OEE", "Refugo", "Energia (kWh/t)"],
        ["Fundição Ponta Grossa I", "48.000", "91%", "78%", "3,8%", "610"],
        ["Fundição Ponta Grossa II", "42.000", "88%", "75%", "4,2%", "635"],
        ["Fundição Limeira", "30.000", "84%", "72%", "4,9%", "660"],
        ["Fundição Divinópolis", "22.000", "79%", "70%", "5,1%", "650"],
        ["Fundição Itajaí", "26.000", "86%", "74%", "4,0%", "620"],
        ["Fundição Santa Maria", "18.000", "73%", "68%", "4,6%", "675"]], [120, 90, 60, 50, 55, 80]),
 ("h", "3. Qualidade no cliente"),
 "PPM consolidado no cliente de 31 (meta 25). O principal ofensor foi porosidade em cabeçotes comerciais da Fundição Limeira, com plano de ação de controle de umidade da areia concluído em setembro.",
 ("h", "4. Segurança e sustentabilidade"),
 "Taxa de frequência de acidentes com afastamento: 0,62. Reaproveitamento de areia de fundição: 87%. Participação de energia renovável na matriz: 64%.",
 ("h", "5. Prioridades para o 4T26"),
 "(i) Ampliar a usinagem de cubos em Rio Claro; (ii) reduzir o refugo de Divinópolis para menos de 4,5%; (iii) concluir o PPAP de duas peças para célula de hidrogênio; (iv) pilotar inspeção por visão computacional nas linhas de blocos.",
])
