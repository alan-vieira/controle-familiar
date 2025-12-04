# connection.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL não definida.")
    return psycopg2.connect(
        database_url,
        sslmode='require',
        cursor_factory=RealDictCursor
    )
