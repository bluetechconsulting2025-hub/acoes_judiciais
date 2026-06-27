import streamlit as st
from db import get_conn
from utils_pdf import gerar_recibo_pdf

st.title("📄 Reimpressão de Recibo")

conn = get_conn()
cur = conn.cursor()

disp_id = st.number_input("Digite o ID da dispensação", min_value=1)

if st.button("Buscar"):
    cur.execute("""
        SELECT 
            d.id,
            p.nome,
            a.numero_processo,
            a.medicamento,
            d.data,
            d.quantidade,
            d.marca,
            d.lote,
            d.validade,
            d.comparecimento,
            d.entregue,
            d.responsavel
        FROM dispensacoes d
        JOIN acoes a ON a.id = d.acao_id
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE d.id = %s
    """, (disp_id,))
    
    dados = cur.fetchone()

    if not dados:
        st.error("Nenhuma dispensação encontrada com esse ID.")
        st.stop()

    (
        id_disp,
        nome,
        processo,
        medicamento,
        data_saida,
        qtd_fornecida,
        marca,
        lote,
        validade,
        comparecimento,
        entregue,
        responsavel
    ) = dados

    def safe(v):
        return str(v) if v is not None else "—"

    marca = safe(marca)
    lote = safe(lote)
    validade = safe(validade)
    comparecimento = safe(comparecimento)
    entregue = safe(entregue)
    responsavel = safe(responsavel)
    data_saida = safe(data_saida)

    st.success("Registro encontrado!")

    st.write(f"**Paciente:** {nome}")
    st.write(f"**Processo:** {processo}")
    st.write(f"**Medicamento:** {medicamento}")
    st.write(f"**Quantidade fornecida:** {qtd_fornecida}")
    st.write(f"**Data:** {data_saida}")
    st.write(f"**Marca:** {marca}")
    st.write(f"**Lote:** {lote}")
    st.write(f"**Validade:** {validade}")
    st.write(f"**Comparecimento:** {comparecimento}")
    st.write(f"**Entregue:** {entregue}")
    st.write(f"**Responsável:** {responsavel}")

    caminho_pdf = f"recibo_disp_{id_disp}.pdf"

    gerar_recibo_pdf(
        caminho_pdf,
        nome,
        processo,
        medicamento,
        marca,
        lote,
        validade,
        "—",              # qtd_fornecer não existe na reimpressão
        qtd_fornecida,
        data_saida,
        entregue,
        responsavel,
        comparecimento,
        id_disp
    )

    with open(caminho_pdf, "rb") as f:
        st.download_button(
            label="📄 Baixar Recibo em PDF",
            data=f,
            file_name=caminho_pdf,
            mime="application/pdf"
        )
