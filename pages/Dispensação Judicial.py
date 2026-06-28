import streamlit as st
from db import get_conn
from datetime import date
from utils_pdf import gerar_recibo_pdf

st.set_page_config(
    page_title="Judicial Blue",
    page_icon="simpl_blue.png",   # pode ser PNG, ICO ou emoji
    layout="wide"
)
st.title("📝 Dispensação Judicial")

conn = get_conn()
cur = conn.cursor()

st.subheader("Registrar entrega de medicamento")

cur.execute("""
    SELECT a.id, p.nome, a.numero_processo, a.medicamento, a.quantidade_medicamento, a.prazo, a.data_receita, a.numero_pasta
    FROM acoes a
    JOIN pacientes p ON p.id = a.paciente_id
    ORDER BY a.id DESC
""")
acoes = cur.fetchall()

if not acoes:
    st.warning("Nenhuma ação judicial cadastrada ainda.")
else:
    acao_map = {
        f"{nome} — Proc: {proc} — Med: {med}": (id, qtd, prazo, data_receita, numero_pasta)
        for id, nome, proc, med, qtd, prazo, data_receita, numero_pasta in acoes
    }

    escolha = st.selectbox("Selecione o paciente / processo", list(acao_map.keys()))
    acao_id, qtd_total, prazo_acao, data_receita, numero_pasta = acao_map[escolha]

    st.info(f"📅 Data de Cumprimento do Processo: {prazo_acao}")
    st.info(f"📋 Número da Pasta: {numero_pasta or '—'}")
    st.info(f"🧾 Data da Receita: {data_receita or '—'}")

    cur.execute("""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM dispensacoes
        WHERE acao_id = %s
    """, (acao_id,))
    total_dispensado = cur.fetchone()[0]

    restante = qtd_total - total_dispensado

    st.info(f"Quantidade total da ação: {qtd_total}")
    st.info(f"Total já dispensado: {total_dispensado}")
    st.info(f"Quantidade restante: {restante}")

    if restante <= 0:
        st.success("✔ Toda a quantidade já foi dispensada. Ação encerrada.")
        st.stop()

    data_saida = st.date_input("Data de saída", value=date.today())
    comparecimento = st.selectbox("Comparecimento", ["Sim", "Não"])
    entregue = st.selectbox("Medicamento entregue?", ["Sim", "Não"])
    marca = st.text_input("Marca do produto")
    lote = st.text_input("Lote do produto")
    validade = st.date_input("Validade do produto")

    qtd_fornecer = st.number_input("Quantidade a fornecer", min_value=1, max_value=restante, value=restante)
    qtd_fornecida = st.number_input("Quantidade fornecida", min_value=0, max_value=qtd_fornecer)

    responsavel = st.text_input("Responsável pela liberação")

    if st.button("Registrar entrega"):
        if not responsavel.strip():
            st.error("Informe o nome do responsável pela liberação.")
            st.stop()

        cur.execute("""
            INSERT INTO dispensacoes 
            (acao_id, data, quantidade, marca, lote, validade, comparecimento, entregue, responsavel)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            acao_id,
            data_saida,
            qtd_fornecida,
            marca,
            lote,
            validade,
            comparecimento,
            entregue,
            responsavel
        ))
        dispensacao_id = cur.fetchone()[0]
        conn.commit()

        cur.execute("""
            SELECT p.nome, a.numero_processo, a.medicamento
            FROM acoes a
            JOIN pacientes p ON p.id = a.paciente_id
            WHERE a.id = %s
        """, (acao_id,))
        nome, processo, medicamento = cur.fetchone()

        cur.execute("SELECT descricao FROM produtos WHERE sku = %s", (medicamento,))
        descricao_med = cur.fetchone()
        nome_medicamento = descricao_med[0] if descricao_med else medicamento

        cur.execute("""
            SELECT COALESCE(SUM(quantidade), 0)
            FROM dispensacoes WHERE acao_id = %s
        """, (acao_id,))
        total_dispensado = cur.fetchone()[0]

        restante = qtd_total - total_dispensado

        if restante <= 0:
            novo_status = "ENCERRADA"
            cur.execute("""
                UPDATE acoes SET status = %s, data_encerramento = %s
                WHERE id = %s
            """, (novo_status, date.today(), acao_id))
        else:
            novo_status = "ATENDIDA PARCIALMENTE" if restante < qtd_total else "ABERTA"
            cur.execute("""
                UPDATE acoes SET status = %s
                WHERE id = %s
            """, (novo_status, acao_id))

        conn.commit()

        caminho_pdf = f"recibo_disp_{dispensacao_id}.pdf"

        gerar_recibo_pdf(
            caminho_pdf,
            nome,
            processo,
            nome_medicamento,
            marca,
            lote,
            str(validade),
            qtd_fornecer,
            qtd_fornecida,
            str(data_saida),
            entregue,
            responsavel,
            comparecimento,
            dispensacao_id,
            numero_pasta,
            data_receita
        )

        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="📄 Baixar Recibo em PDF",
                data=f,
                file_name=caminho_pdf,
                mime="application/pdf"
            )

        st.success(f"Entrega registrada! ID da dispensação: {dispensacao_id}")
