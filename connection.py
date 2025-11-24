# connection.py (versão aprimorada)
import psycopg2
from contextlib import contextmanager
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode='require',
            connect_timeout=10  # ← Importante para produção
        )
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Erro de conexão com o banco de dados: {e}")
        raise
    finally:
        if conn:
            conn.close()