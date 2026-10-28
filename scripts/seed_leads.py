"""Gera 400 leads FICTÍCIOS no Lakebase (cadastro.leads) — o CDC replica p/ dadosapp.fundalis_cdc.lb_leads_history.
Contatos claramente fictícios: e-mail em domínio reservado .example, DDD 00 e CNPJ com dígito verificador INVÁLIDO."""
import random, datetime as dt
from pg import conn
R = random.Random(42)
NOMES = ['João','Marcos','Luiz','Sebastião','Antônio','Carlos','Rodrigo','Paulo','Cláudio','Fernando','Ricardo','Eduardo','Roberto','Gustavo','Vicente','Nelson','Adriano','Wilson','Maria','Fernanda','Juliana','Patrícia','Camila','Letícia','Renata','Beatriz']
SOBRE = ['Alves','Souza','Menezes','Ferreira','Oliveira','Fontana','Maggi','Bueno','Zanatta','Nishimura','Schneider','Pivetta','Dalpiaz','Marchesan','Rossi','Costa','Scheffer','Bertaso','Moretto','Griebeler']
EMP = ['Powertrain','Motores','Diesel','Off-Road','Industrial','AutoPeças','Máquinas','Metalúrgica','Comercial','Global','Sul','Atlântico','Precision','Forge','Drivetrain','Mobilidade']
SEG = ['Automotivo Leve','Comercial & Caminhões','Off-Road & Agrícola','Industrial','Hidrogênio & Energia']
CID = [('São Paulo','SP','Sudeste'),('Rio de Janeiro','RJ','Sudeste'),('Belo Horizonte','MG','Sudeste'),('Curitiba','PR','Sul'),('Porto Alegre','RS','Sul'),('Salvador','BA','Nordeste'),('Recife','PE','Nordeste'),('Goiânia','GO','Centro-Oeste'),('Joinville','SC','Sul'),('Campinas','SP','Sudeste'),('Caxias do Sul','RS','Sul'),('Betim','MG','Sudeste'),('Sorocaba','SP','Sudeste'),('Cuiabá','MT','Centro-Oeste')]
CANAL = ['Feira/Evento','Indicação','Site','Representante','RFQ','Cliente OEM']
STATUS = ['Novo','Novo','Em contato','Cotação','Proposta','Fechado','Perdido']
PROD = ['Bloco de Motor Diesel CGI','Bloco de Motor Flex','Bloco V8 Diesel','Bloco Agrícola Off-Road','Cabeçote Diesel Pesado','Cabeçote Comercial','Cabeçote Flex','Braço de Controle','Suporte de Motor','Componente de Suspensão','Cubo de Roda','Carcaça de Diferencial','Carcaça de Turbina','Coletor de Escape','Múltiplo de Admissão','Virabrequim Usinado','Disco de Freio','Cubo Usinado Completo']
# (mensagem, score_base, sentimento, resumo, próxima ação) — textos fictícios
MSG = [
 ('Apenas comparando preço de bloco de motor, sem previsão de compra no momento.', 20, 'Neutro', '{n} está só comparando preços de bloco de motor, sem prazo de compra.', 'Enviar tabela de referência e agendar retorno com {n} em 60 dias.'),
 ('Avaliando fornecedor de cabeçote diesel em CGI; comparando fundições.', 45, 'Neutro', '{n} avalia fornecedores de cabeçote diesel em CGI.', 'Apresentar a {n} o case técnico de CGI e propor visita ao Centro Técnico.'),
 ('Quer entender a diferença entre ferro nodular e vermicular (CGI) antes de decidir.', 40, 'Positivo', '{n} quer entender nodular × vermicular antes de decidir.', 'Enviar a {n} a ficha técnica comparativa de materiais.'),
 ('RFQ de 5.000 blocos de motor diesel CGI por ano para linha pesada.', 88, 'Positivo', '{n} enviou RFQ de 5.000 blocos diesel CGI/ano.', 'Montar proposta para {n} com engenharia de aplicação em até 5 dias.'),
 ('Precisa de coletor de escape em nodular austemperado, amostra urgente.', 78, 'Positivo', '{n} precisa de amostra urgente de coletor de escape SiMo.', 'Priorizar lote-piloto e confirmar prazo de amostra com {n}.'),
 ('Interesse em usinagem completa de cubo de roda com furação pronta.', 65, 'Positivo', '{n} tem interesse em cubo de roda com usinagem completa.', 'Agendar reunião técnica com {n} para tolerâncias e volumes.'),
 ('Desenvolvimento de componente estrutural nodular para nova plataforma.', 70, 'Positivo', '{n} quer desenvolver componente estrutural nodular p/ nova plataforma.', 'Envolver o time de desenvolvimento e enviar NDA para {n}.'),
 ('Solicitou proposta de cabeçotes para linha de veículos comerciais.', 74, 'Positivo', '{n} pediu proposta de cabeçotes para veículos comerciais.', 'Enviar proposta comercial a {n} e marcar follow-up em 7 dias.'),
 ('Fechar pedido de discos de freio ainda este trimestre.', 85, 'Positivo', '{n} quer fechar pedido de discos de freio neste trimestre.', 'Emitir pedido e alinhar cronograma de entrega com {n}.'),
 ('Reclamou de atraso na última entrega de carcaças; avalia trocar de fornecedor.', 30, 'Negativo', '{n} reclamou de atraso e cogita trocar de fornecedor.', 'Escalar para a gerência e ligar para {n} com plano de ação em 24h.'),
 ('Pedido recorrente de carcaças de diferencial para o mercado de reposição.', 80, 'Positivo', '{n} tem pedido recorrente de carcaças de diferencial.', 'Propor a {n} contrato anual com programação de entregas.'),
 ('Projeto de peça fundida para célula de hidrogênio; pronto para cotar.', 76, 'Positivo', '{n} tem projeto de peça para célula de hidrogênio pronto para cotar.', 'Encaminhar o projeto de {n} à área de Novos Negócios para cotação.'),
]
def cnpj():
    """CNPJ no formato oficial mas com os 2 dígitos verificadores propositalmente ERRADOS (nunca é um CNPJ real)."""
    d = [R.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for pesos in ([5,4,3,2,9,8,7,6,5,4,3,2], [6,5,4,3,2,9,8,7,6,5,4,3,2]):
        sm = sum(a*b for a, b in zip(d, pesos)) % 11; d.append(0 if sm < 2 else 11 - sm)
    d[12] = (d[12] + 1) % 10; d[13] = (d[13] + 3) % 10
    s = "".join(map(str, d)); return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
import unicodedata
def slug(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if c.isalnum() and unicodedata.category(c) != "Mn")
rows = []
now = dt.datetime.now(dt.timezone.utc)
for i in range(1, 401):
    n, s = R.choice(NOMES), R.choice(SOBRE); nome = f"{n} {s}"
    emp = f"{R.choice(['Cliente','Grupo','Indústria'])} {R.choice(EMP)} (fictícia)"
    cid, uf, reg = R.choice(CID)
    msg, sb, sent, res, acao = R.choice(MSG)
    score = max(0, min(100, sb + R.randint(-12, 12)))
    classe = 'Quente' if score >= 70 else ('Morno' if score >= 40 else 'Frio')
    tel = f"(00) 9{R.randint(1000,9999)}-{R.randint(1000,9999)}"
    email = f"{slug(n)}.{slug(s)}@{slug(emp.replace('(fictícia)',''))}.example"
    dc = now - dt.timedelta(days=R.randint(0, 60), hours=R.randint(0, 23))
    rows.append((f"LEAD-{i:06d}", nome, email, tel, cnpj(), emp, R.choice(SEG), R.choice(PROD), cid, uf, reg,
                 R.choice(CANAL), R.choice(STATUS), msg, classe, score, sent, res.format(n=nome), acao.format(n=nome),
                 dc, dc + dt.timedelta(minutes=5), 'seed', dc))
with conn() as c:
    with c.cursor() as cur:
        cur.executemany("""INSERT INTO cadastro.leads (lead_id, cliente_nome, email, telefone, documento, empresa, segmento,
            produto_nome, cidade, uf, regiao, canal, status, mensagem, classificacao_ia, score_ia, sentimento_ia, resumo_ia,
            proxima_acao_ia, data_contato, enriquecido_em, criado_por, atualizado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (lead_id) DO NOTHING""", rows)
    print(c.execute("select count(*), count(distinct cliente_nome) from cadastro.leads").fetchone())
