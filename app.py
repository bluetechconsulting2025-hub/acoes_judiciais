import streamlit as st
from db import get_conn
from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText
import os

st.set_page_config(
    page_title="Judicial Blue",
    page_icon="simpl_blue.png",   # pode ser PNG, ICO ou emoji
    layout="wide"
)


st.title("⚖️ Sistema de Ações Judiciais – POC")
st.write("Use o menu à esquerda para navegar entre os módulos.")

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
    hoje = date.today()
    alerta_3_dias = hoje + timedelta(days=3)

    hoje_str = hoje.strftime("%Y-%m-%d")
    alerta_3_dias_str = alerta_3_dias.strftime("%Y-%m-%d")

    # ALERTA DE 3 DIAS
    cur.execute("""
        SELECT a.id, a.numero_processo, a.prazo, p.nome, p.cpf, p.email
        FROM acoes a
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE a.prazo = %s
        AND a.status != 'ENCERRADA'
    """, (alerta_3_dias_str,))
    proximos = cur.fetchall()

    for acao_id, processo, prazo, nome, cpf, email in proximos:
        cur.execute(
            "SELECT 1 FROM alertas_enviados WHERE acao_id=%s AND tipo_alerta='3dias'",
            (acao_id,)
        )
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

    # ALERTA VENCE HOJE
    cur.execute("""
        SELECT a.id, a.numero_processo, a.prazo, p.nome, p.cpf, p.email
        FROM acoes a
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE a.prazo = %s
        AND a.status != 'ENCERRADA'
    """, (hoje_str,))
    hoje_lista = cur.fetchall()

    for acao_id, processo, prazo, nome, cpf, email in hoje_lista:
        cur.execute(
            "SELECT 1 FROM alertas_enviados WHERE acao_id=%s AND tipo_alerta='hoje'",
            (acao_id,)
        )
        ja_enviado = cur.fetchone()

        if ja_enviado or not email:
            continue

        ok = enviar_email(
            email,
            f"🚨 URGENTE: Processo {processo} vence HOJE",
            f"O processo {processo} do paciente {nome} (CPF {cpf}) vence hoje.\nData limite: {prazo}"
        )
        if ok:
            cur.execute("""
                INSERT INTO alertas_enviados (acao_id, tipo_alerta, data_envio)
                VALUES (%s, 'hoje', %s)
            """, (acao_id, hoje_str))
            conn.commit()

    # ALERTA DE ATRASO
    cur.execute("""
        SELECT a.id, a.numero_processo, a.prazo, p.nome, p.cpf, p.email
        FROM acoes a
        JOIN pacientes p ON p.id = a.paciente_id
        WHERE a.prazo < %s
        AND a.status != 'ENCERRADA'
    """, (hoje_str,))
    atrasados = cur.fetchall()

    for acao_id, processo, prazo, nome, cpf, email in atrasados:
        cur.execute(
            "SELECT 1 FROM alertas_enviados WHERE acao_id=%s AND tipo_alerta='atraso'",
            (acao_id,)
        )
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


# Dispara ao carregar a página
verificar_alertas_pendencias()


# ----------------------------
# ALERTA DE PRAZOS JUDICIAIS
# ----------------------------
st.subheader("⏰ Alertas de Prazos Judiciais")

hoje = date.today()
limite = hoje + timedelta(days=3)
hoje_str = hoje.strftime("%Y-%m-%d")
limite_str = limite.strftime("%Y-%m-%d")

cur.execute("""
    SELECT p.nome, a.numero_processo, a.medicamento, a.prazo
    FROM acoes a
    JOIN pacientes p ON p.id = a.paciente_id
    WHERE a.prazo < %s
    AND a.status != 'ENCERRADA'
    ORDER BY a.prazo ASC
""", (hoje_str,))
vencidos = cur.fetchall()

cur.execute("""
    SELECT p.nome, a.numero_processo, a.medicamento, a.prazo
    FROM acoes a
    JOIN pacientes p ON p.id = a.paciente_id
    WHERE a.prazo BETWEEN %s AND %s
    AND a.status != 'ENCERRADA'
    ORDER BY a.prazo ASC
""", (hoje_str, limite_str))
proximos = cur.fetchall()

if vencidos:
    st.error("⚠️ PRAZOS VENCIDOS — ação judicial em risco!")
    st.table(vencidos)

if proximos:
    st.warning("🔶 PRAZOS PRÓXIMOS DO VENCIMENTO (até 3 dias)")
    st.table(proximos)

if not vencidos and not proximos:
    st.success("✔ Nenhum prazo crítico no momento.")
