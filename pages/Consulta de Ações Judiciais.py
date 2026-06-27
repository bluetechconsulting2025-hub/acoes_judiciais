import streamlit as st
import pandas as pd
from db import get_conn

st.set_page_config(layout="wide")

st.title("📄 Consulta de Ações Judiciais")

conn = get_conn()
cur = conn.cursor()

if st.button("➕ Cadastrar nova ação"):
    st.switch_page("pages/Ações_Judiciais.py")

st.subheader("🔍 Filtros")

col1, col2 = st.columns(2)

filtro_cpf = col1.text_input("Filtrar por CPF")
filtro_processo = col2.text_input("Filtrar por Número do Processo")

query = """
    SELECT 
        a.id,
        p.nome,
        p.cpf,
        a.numero_processo,
        a.medicamento,
        a.quantidade_medicamento,
        COALESCE((SELECT SUM(quantidade) FROM dispensacoes d WHERE d.acao_id = a.id), 0) AS dispensado,
        a.prazo,
        a.status,
        a.data_encerramento,
        (
            SELECT STRING_AGG(d.id::text, ', ')
            FROM dispensacoes d
            WHERE d.acao_id = a.id
        ) AS ids_dispensacoes
    FROM acoes a
    JOIN pacientes p ON p.id = a.paciente_id
    WHERE 1=1
"""

params = []

if filtro_cpf.strip():
    query += " AND p.cpf LIKE %s"
    params.append(f"%{filtro_cpf}%")

if filtro_processo.strip():
    query += " AND a.numero_processo LIKE %s"
    params.append(f"%{filtro_processo}%")

query += " ORDER BY a.id DESC"

cur.execute(query, params)
dados = cur.fetchall()

colunas = [
    "ID",
    "Paciente",
    "CPF",
    "Número do Processo",
    "Medicamento",
    "Quantidade Total",
    "Total Dispensado",
    "Data de Cumprimento do Processo",
    "Status",
    "Data de Encerramento",
    "IDs de Dispensação"
]

df = pd.DataFrame(dados, columns=colunas)

st.subheader("📊 Indicadores")

total_acoes = len(df)
encerradas = (df["Status"] == "ENCERRADA").sum()
parciais = (df["Status"] == "ATENDIDA PARCIALMENTE").sum()
abertas = (df["Status"] == "ABERTA").sum()

colA, colB, colC, colD = st.columns(4)

colA.metric("Total de Ações", total_acoes)
colB.metric("Encerradas", encerradas)
colC.metric("Parcialmente Atendidas", parciais)
colD.metric("Abertas", abertas)

st.subheader("📁 Resultados da Consulta")

st.dataframe(df, use_container_width=True)
