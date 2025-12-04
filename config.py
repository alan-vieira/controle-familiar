# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Usando os mesmos nomes que você definiu no Render
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não definida no ambiente.")

# SECRET_KEY está definida no Render, mas NÃO é usada no código
# (mantemos apenas para evitar erros se o Flask exigir em alguns contextos)
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-para-desenvolvimento')
