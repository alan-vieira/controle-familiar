import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuração para Supabase ---
DATABASE_URL = os.getenv('DATABASE_URL')

# --- Chave Secreta para Sessão de Login ---
SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_aleatoria_segura') # Defina uma chave forte no Render
