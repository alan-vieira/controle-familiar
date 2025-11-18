import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuração para Supabase ---
DATABASE_URL = os.getenv('DATABASE_URL')

# --- Chave Secreta para Sessão de Login ---
SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_aleatoria_segura') # Defina uma chave forte no Render

if not DATABASE_URL:
    print("Aviso: DATABASE_URL não encontrada. Usando variáveis antigas (DB_HOST, etc.).")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5455")
    DB_NAME = os.getenv("DB_NAME", "control_fin")
    DB_USER = os.getenv("DB_USER", "postgresUser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgresPW")

    if not DB_PASSWORD:
        raise ValueError("DB_PASSWORD não definida no .env")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
