from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime

def gerar_recibo_pdf(
    caminho,
    paciente,
    processo,
    medicamento,
    marca,
    lote,
    validade,
    qtd_fornecer,
    qtd_fornecida,
    data_saida,
    entregue,
    responsavel,
    comparecimento,
    id_dispensacao,
    numero_pasta=None,
    data_receita=None
):
    def safe(v):
        return str(v) if v is not None else "—"

    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    try:
        logo = ImageReader("logo_blue.png")
        c.drawImage(logo, largura - 160, altura - 120, width=120, height=60, preserveAspectRatio=True, mask='auto')
    except:
        pass

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(largura / 2, altura - 50, "RECIBO DE DISPENSA JUDICIAL")
    c.line(40, altura - 60, largura - 40, altura - 60)

    y = altura - 140
    c.setFont("Helvetica", 13)

    campos = [
        ("ID da Dispensação",           safe(id_dispensacao)),
        ("Paciente",                     safe(paciente)),
        ("Número do Processo",           safe(processo)),
        ("Número da Pasta",              safe(numero_pasta)),
        ("Data da Receita",              safe(data_receita)),
        ("Medicamento",                  safe(medicamento)),
        ("Marca",                        safe(marca)),
        ("Lote",                         safe(lote)),
        ("Validade",                     safe(validade)),
        ("Quantidade a Fornecer",        safe(qtd_fornecer)),
        ("Quantidade Fornecida",         safe(qtd_fornecida)),
        ("Data de Saída",                safe(data_saida)),
        ("Entregue?",                    safe(entregue)),
        ("Comparecimento",               safe(comparecimento)),
        ("Responsável pela Liberação",   safe(responsavel)),
        ("Gerado em",                    datetime.now().strftime("%d/%m/%Y %H:%M"))
    ]

    for label, valor in campos:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(250, y, valor)
        y -= 25

    y -= 40
    c.line(50, y, 250, y)
    c.drawString(50, y - 15, "Assinatura do Paciente")

    c.line(300, y, 550, y)
    c.drawString(300, y - 15, f"Assinatura do Responsável ({safe(responsavel)})")

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(largura / 2, 40, "Documento gerado automaticamente pelo Sistema Judicial Blue")

    c.save()