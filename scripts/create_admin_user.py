# scripts/create_admin_simple.py (versão aprimorada)
import os
import psycopg2
from werkzeug.security import generate_password_hash

def get_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL não encontrada")
        exit(1)
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def create_admin_simple():
    username = "admin"
    password = "admin123"
    email = "admin@familia.com"
    password_hash = generate_password_hash(password)
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                username VARCHAR(150) NOT NULL UNIQUE,
                email VARCHAR(255),
                password_hash VARCHAR(255) NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT true
            )
        """)
        
        cur.execute("""
            INSERT INTO usuario (username, email, password_hash)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, (username, email, password_hash))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Usuário admin garantido no banco!")
        print(f"   Username: {username}")
        print(f"   Password: {password} (altere após o primeiro login!)")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    create_admin_simple()