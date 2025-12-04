# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não definida no ambiente.")

SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-para-desenvolvimento')

# Apenas se estiver validando tokens no backend:
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

if not SUPABASE_URL or not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_URL e SUPABASE_JWT_SECRET são necessários para autenticação.")