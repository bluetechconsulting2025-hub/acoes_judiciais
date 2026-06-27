import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

def get_conn():
    """
    Cria e retorna uma conexão com o banco PostgreSQL do Supabase.
    """
    return psycopg2.connect(
        host=os.getenv("SUPABASE_HOST"),
        port="5432",
        database=os.getenv("SUPABASE_DB"),
        user=os.getenv("SUPABASE_USER"),
        password=os.getenv("SUPABASE_PASS")
    )
