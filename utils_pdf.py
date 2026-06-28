from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def gerar_recibo_pdf(
    caminho_pdf,
    paciente,
    numero_processo,
    medicamento,
    marca,
    lote,
    validade,
    quantidade_fornecer,
    quantidade_fornecida,
    data_saida,
    entregue,
    responsavel,
    comparecimento,
    id_disp,
    numero_pasta=None,
    data_receita=None
):
    """
    Gera o PDF do recibo de dispensação judicial.
    Compatível com emissão e reimpressão.
    """

    c = canvas.Canvas(caminho_pdf, pagesize=letter)

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "RECIBO DE DISPENSA JUDICIAL")

    c.setFont("Helvetica", 12)

    y = 720
    linha = 20

    def add(label, value):
        nonlocal y
        if value is None or value == "":
            value = "—"
        c.drawString(50, y, f"{label}: {value}")
        y -= linha

    # Campos
    add("ID da Dispensação", id_disp)
    add("Paciente", paciente)
    add("Número do Processo", numero_processo)
    add("Número da Pasta", numero_pasta)
    add("Data da Receita", data_receita)
    add("Medicamento", medicamento)
    add("Marca", marca)
    add("Lote", lote)
    add("Validade", validade)
    add("Quantidade a Fornecer", quantidade_fornecer)
    add("Quantidade Fornecida", quantidade_fornecida)
    add("Data de Saída", data_saida)
    add("Entregue?", entregue)
    add("Comparecimento", comparecimento)
    add("Responsável pela Liberação", responsavel)

    c.save()
