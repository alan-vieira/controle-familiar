# connection.py
import psycopg2
from contextlib import contextmanager
from config import DATABASE_URL # Importar a string de conexão consolidada

@contextmanager
def get_db_connection():
    # Supabase geralmente requer SSL
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    try:
        yield conn
    finally:
        conn.close()
