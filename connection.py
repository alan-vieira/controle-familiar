# connection.py (recomendado)
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """
    Estabelece conexão com o banco de dados PostgreSQL (Supabase/Render)
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL não encontrada nas variáveis de ambiente")
    
    # psycopg2 >= 2.8 aceita 'postgresql://' diretamente
    conn = psycopg2.connect(
        database_url,
        sslmode='require',  # obrigatório para Supabase
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    """
    Cria as tabelas conforme seu schema final
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                username VARCHAR(150) NOT NULL UNIQUE,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT true
            )
        ''')
        conn.commit()
        print("✅ Tabela 'usuario' verificada")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro na inicialização do DB: {e}")
        raise
    finally:
        cur.close()
        conn.close()
