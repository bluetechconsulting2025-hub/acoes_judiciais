import streamlit as st
import requests
import base64
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from db import get_conn
import os

st.set_page_config(layout="wide")
st.title("⚖️ Cadastro de Ações Judiciais")

conn = get_conn()
cur = conn.cursor()


# -----------------------------
# FUNÇÃO: ENVIAR EMAIL
# -----------------------------
def enviar_email(destinatarios, assunto, mensagem):
    remetente = st.secrets["SMTP_USER"]
    senha = st.secrets["SMTP_PASS"]

    if isinstance(destinatarios, str):
        destinatarios = [d.strip() for d in destinatarios.split(",") if d.strip()]

    msg = MIMEText(mensagem, "plain", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remetente, senha)
            smtp.sendmail(remetente, destinatarios, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


# -----------------------------
# FUNÇÃO: VERIFICAR ALERTAS
# -----------------------------
def verificar_alertas_pendencias():
    hoje = datetime.now().date()
    alerta_3_dias = hoje + timedelta(days=3)

    hoje_str = hoje.strftime("%Y-%m-%d")
    alerta_3_dias_str = alerta_3_dias.strftime("%Y-%m-%d")

    # ALERTA DE 3 DIAS
    cur.execute("""
        SELECT a.id, a.numero_processo, a.prazo, p.nome, p.cpf, p.email
        FROM acoes a
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE a.prazo = %s AND a.status != 'ENCERRADA'
    """, (alerta_3_dias_str,))
    proximos = cur.fetchall()

    for acao_id, processo, prazo, nome, cpf, email in proximos:
        cur.execute("SELECT 1 FROM alertas_enviados WHERE acao_id=%s AND tipo_alerta='3dias'", (acao_id,))
        ja_enviado = cur.fetchone()

        if ja_enviado or not email:
            continue

        ok = enviar_email(
            email,
            f"⚠️ Alerta: Processo {processo} vence em 3 dias",
            f"O processo {processo} do paciente {nome} (CPF {cpf}) vence em 3 dias.\nData limite: {prazo}"
        )
        if ok:
            cur.execute("""
                INSERT INTO alertas_enviados (acao_id, tipo_alerta, data_envio)
                VALUES (%s, '3dias', %s)
            """, (acao_id, hoje_str))
            conn.commit()

    # ALERTA DE ATRASO
    cur.execute("""
        SELECT a.id, a.numero_processo, a.prazo, p.nome, p.cpf, p.email
        FROM acoes a
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE a.prazo < %s AND a.status != 'ENCERRADA'
    """, (hoje_str,))
    atrasados = cur.fetchall()

    for acao_id, processo, prazo, nome, cpf, email in atrasados:
        cur.execute("SELECT 1 FROM alertas_enviados WHERE acao_id=%s AND tipo_alerta='atraso'", (acao_id,))
        ja_enviado = cur.fetchone()

        if ja_enviado or not email:
            continue

        ok = enviar_email(
            email,
            f"⛔ Atraso: Processo {processo} está vencido",
            f"O processo {processo} do paciente {nome} (CPF {cpf}) está atrasado.\nData limite era: {prazo}"
        )
        if ok:
            cur.execute("""
                INSERT INTO alertas_enviados (acao_id, tipo_alerta, data_envio)
                VALUES (%s, 'atraso', %s)
            """, (acao_id, hoje_str))
            conn.commit()


# -----------------------------
# FUNÇÃO: GERAR TOKEN WMS
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


# -----------------------------
# FUNÇÃO: ENVIAR AÇÃO PARA WMS
# -----------------------------
def enviar_para_wms(processo, sku, quantidade):
    token, erro = gerar_token_wms()
    if erro:
        st.error(erro)
        return
    if not token:
        st.error("Token não recebido do servidor WMS.")
        return

    url = "https://mingle-ionapi.inforcloudsuite.com/BLUELOGISTICA_PRD/WM/wmwebservice_rest/BLUELOGISTICA_PRD_BLUELOGISTICA_PRD_SCE_PRD_0_wmwhse2/receipts"
    payload = {
        "receiptkey": processo,
        "storerkey": "BLUE SUPPLY",
        "type": "50",
        "receiptdetails": [{
            "receiptkey": processo,
            "sku": sku,
            "storerkey": "BLUE SUPPLY",
            "qtyexpected": quantidade,
            "lottable02": processo
        }]
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code in (200, 201):
            st.success("Entrada registrada no WMS com sucesso!")
        else:
            st.error(f"Erro ao enviar para o WMS: {resp.status_code}")
            st.error(resp.text)
    except Exception as e:
        st.error(f"Falha ao conectar ao WMS: {str(e)}")


# -----------------------------
# FORMULÁRIO DE CADASTRO
# -----------------------------
st.subheader("Nova Ação Judicial")

col1, col2 = st.columns(2)

with col1:
    nome_paciente = st.text_input("Nome do paciente")
    cpf = st.text_input("CPF")
    email = st.text_input("E-mail(s) do responsável (separe por vírgula)")
    numero_processo = st.text_input("Número do processo")
    numero_pasta = st.text_input("Número da pasta")
    data_receita = st.date_input("Data da receita")

with col2:
    cur.execute("SELECT sku, descricao FROM produtos ORDER BY descricao")
    produtos = cur.fetchall()

    lista_descricoes = [descricao for sku, descricao in produtos]
    descricao_escolhida = st.selectbox("Medicamento", lista_descricoes)
    sku = next(sku for sku, descricao in produtos if descricao == descricao_escolhida)

    quantidade_medicamento = st.number_input("Quantidade solicitada", min_value=1, value=1)
    prazo = st.date_input("Data de Cumprimento do Processo")
    status_inicial = st.selectbox("Status inicial", ["ABERTA", "ATENDIDA PARCIALMENTE", "ENCERRADA"])

if st.button("Salvar ação judicial"):
    if not (nome_paciente.strip() and cpf.strip() and numero_processo.strip()):
        st.error("Preencha todos os campos obrigatórios.")
    else:
        # Inserir paciente
        cur.execute("""
            INSERT INTO pacientes (nome, cpf, email)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (nome_paciente, cpf, email))
        paciente_id = cur.fetchone()[0]

        # Inserir ação judicial
        cur.execute("""
            INSERT INTO acoes (paciente_id, numero_processo, medicamento, quantidade_medicamento, status, prazo, data_receita, numero_pasta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            paciente_id,
            numero_processo,
            sku,
            quantidade_medicamento,
            status_inicial,
            prazo,
            data_receita,
            numero_pasta
        ))
        acao_id = cur.fetchone()[0]
        conn.commit()

        st.success(f"Ação judicial criada com sucesso! ID: {acao_id}")

        enviar_para_wms(numero_processo, sku, quantidade_medicamento)
        verificar_alertas_pendencias()
