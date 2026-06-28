import streamlit as st
from db import get_conn
from datetime import date
from utils_pdf import gerar_recibo_pdf
import requests
import base64

st.set_page_config(
    page_title="Judicial Blue",
    page_icon="simpl_blue.png",
    layout="wide"
)
st.title("📝 Dispensação Judicial")

conn = get_conn()
cur = conn.cursor()


# -----------------------------
# TOKEN WMS
# -----------------------------
def gerar_token_wms():
    token_url = "https://mingle-sso.inforcloudsuite.com:443/BLUELOGISTICA_PRD/as/token.oauth2"
    client_id = "BLUELOGISTICA_PRD~tJklLvAWL1XjXvVNGY9QcXTE_8Ir3Sc4JGqmpjEBKw0"
    client_secret = "BKC6csMmq45Ft-cDuzm22LBR0RJiLGLFhL97UmpmdQ9AoOJ2kLRNlpwcHcdx3ljSYU6pdQTJPvvDSLFLviYzHw"
    username = "BLUELOGISTICA_PRD#jbN0nD1rn_xyHeiTqMNmQ17tQcq7ZjPvFtfEtMeRODCAq0k-MQdsgtyOuvN314gakmR4udEEYCPaARoJ5AdxKw"
    password = "-RJX4RllTNdwbUhAdHZdyIQZ0BEwYHacfT4Absm6ZrUsLljhGGSQoXfQpuRBuOCvz_84GMWdoA5NJcHAtDxYeg"

    auth_base64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_base64}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "password", "username": username, "password": password}

    try:
        resp = requests.post(token_url, headers=headers, data=data, timeout=15)
        if resp.status_code != 200:
            return None, f"Erro ao gerar token: {resp.status_code} - {resp.text}"
        return resp.json().get("access_token"), None
    except Exception as e:
        return None, f"Falha ao conectar ao servidor de token: {str(e)}"


def limpar_cpf(cpf):
    return "".join(filter(str.isdigit, cpf))


# -----------------------------
# SHIPMENTS (primeiro)
# -----------------------------
def criar_shipment_wms(cpf_limpo, processo, sku, quantidade, lote):
    token, erro = gerar_token_wms()
    if erro or not token:
        st.error(erro or "Token não recebido para shipment.")
        return False

    url = "https://mingle-ionapi.inforcloudsuite.com/BLUELOGISTICA_PRD/WM/wmwebservice_rest/BLUELOGISTICA_PRD_BLUELOGISTICA_PRD_SCE_PRD_0_wmwhse2/shipments"

    payload = {
        "orderkey": processo,
        "storerkey": cpf_limpo,
        "type": "50",
        "orderdetails": [{
            "orderkey": processo,
            "sku": sku,
            "storerkey": cpf_limpo,
            "qty": quantidade
        }]
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return True
        else:
            st.error(f"Erro ao criar shipment no WMS: {resp.status_code}")
            st.error(resp.text)
            return False
    except Exception as e:
        st.error(f"Falha ao conectar ao WMS (shipments): {str(e)}")
        return False


# -----------------------------
# APPOINTMENTS (depois do shipment)
# -----------------------------
def criar_appointment_wms(cpf_limpo, processo, data_saida, numero_pedido):
    token, erro = gerar_token_wms()
    if erro or not token:
        st.error(erro or "Token não recebido para appointment.")
        return False

    url = "https://mingle-ionapi.inforcloudsuite.com/BLUELOGISTICA_PRD/WM/wmwebservice_rest/BLUELOGISTICA_PRD_BLUELOGISTICA_PRD_SCE_PRD_0_wmwhse2/appointments"

    payload = {
        "appointmentkey": processo,
        "storerkey": cpf_limpo,
        "type": "1",
        "gmtstartdateandtime": f"{data_saida.strftime('%Y-%m-%d')}T00:00:00-03:00",
        "gmtenddateandtime": f"{data_saida.strftime('%Y-%m-%d')}T01:00:00-03:00"
        "appointmentdetails": [
            {
                "appointmentkey": processo,
                "sourcekey": numero_pedido,
                "sourcetype": 1
            }
        ]
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            return True
        else:
            st.error(f"Erro ao criar appointment no WMS: {resp.status_code}")
            st.error(resp.text)
            return False
    except Exception as e:
        st.error(f"Falha ao conectar ao WMS (appointments): {str(e)}")
        return False


# -----------------------------
# FUNÇÃO COMPLETA DA DISPENSAÇÃO
# -----------------------------
def enviar_dispensacao_wms(cpf_limpo, processo, sku, quantidade, lote, data_saida):
    # shipment primeiro
    if not criar_shipment_wms(cpf_limpo, processo, sku, quantidade, lote):
        return

    # appointment depois
    if not criar_appointment_wms(cpf_limpo, processo, data_saida, processo):
        return

    st.success("Dispensação registrada no WMS (shipment + appointment)!")


# -----------------------------
# TELA DE DISPENSAÇÃO
# -----------------------------
st.subheader("Registrar entrega de medicamento")

cur.execute("""
    SELECT a.id, p.nome, a.numero_processo, a.medicamento, a.quantidade_medicamento, 
           a.prazo, a.data_receita, a.numero_pasta, p.cpf
    FROM acoes a
    JOIN pacientes p ON p.id = a.paciente_id
    ORDER BY a.id DESC
""")
acoes = cur.fetchall()

if not acoes:
    st.warning("Nenhuma ação judicial cadastrada ainda.")
else:
    acao_map = {
        f"{nome} — Proc: {proc} — Med: {med}": (id, qtd, prazo, data_receita, numero_pasta, med, cpf)
        for id, nome, proc, med, qtd, prazo, data_receita, numero_pasta, cpf in acoes
    }

    escolha = st.selectbox("Selecione o paciente / processo", list(acao_map.keys()))
    acao_id, qtd_total, prazo_acao, data_receita, numero_pasta, sku_medicamento, cpf_paciente = acao_map[escolha]

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

        # grava dispensação
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

        # dados para recibo
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

        # recibo PDF
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

        # integração WMS
        cpf_limpo = limpar_cpf(cpf_paciente)

        enviar_dispensacao_wms(
            cpf_limpo,
            processo,
            sku_medicamento,
            qtd_fornecida,
            lote,
            data_saida
        )

        st.success(f"Entrega registrada! ID da dispensação: {dispensacao_id}")
