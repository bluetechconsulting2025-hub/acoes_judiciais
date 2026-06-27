import psycopg2
import streamlit as st

def get_conn():
    return psycopg2.connect(
        host= "aws-1-sa-east-1.pooler.supabase.com",
        database=st.secrets["SUPABASE_DB"],
        user="postgres.dvetmverdsdbegvmrbty",
        password=st.secrets["SUPABASE_PASS"],
        port=5432
    )
