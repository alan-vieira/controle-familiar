import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """
    Estabelece conexão com o banco de dados PostgreSQL
    """
    try:
        # Para Render.com - usa DATABASE_URL do environment
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            raise Exception("DATABASE_URL não encontrada nas variáveis de ambiente")
        
        # Render usa formato postgresql://, mas psycopg2 espera postgres://
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgres://')
        
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar com o banco: {e}")
        raise e

def init_db():
    """
    Inicializa o banco de dados criando as tabelas necessárias
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Tabela de usuários (AGORA COM NOME CORRETO: usuario)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("✅ Tabelas criadas/verificadas com sucesso")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao criar tabelas: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()
