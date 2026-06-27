import psycopg2
import streamlit as st

def get_conn():
    return psycopg2.connect(
        host= "db.dvetmverdsdbegvmrbty.supabase.co",
        database=st.secrets["SUPABASE_DB"],
        user=st.secrets["SUPABASE_USER"],
        password=st.secrets["SUPABASE_PASS"],
        port=5432
    )
