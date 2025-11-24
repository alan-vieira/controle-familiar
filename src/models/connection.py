# connection.py (versão aprimorada)
import psycopg2
from contextlib import contextmanager
<<<<<<< HEAD:connection.py
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)
=======
from src.config.config import DATABASE_URL # Importar a string de conexão consolidada
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/models/connection.py

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