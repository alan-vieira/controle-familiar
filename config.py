# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não definida")

SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_aleatoria_segura')
