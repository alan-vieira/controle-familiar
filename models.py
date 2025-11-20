# models.py
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from connection import get_db_connection

class Usuario(UserMixin):
    def __init__(self, id, username, email, password_hash, criado_em=None, ativo=True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.criado_em = criado_em
        self.ativo = ativo

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get_by_id(user_id):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, username, email, password_hash, criado_em, ativo 
                        FROM usuario 
                        WHERE id = %s AND ativo = true
                    """, (user_id,))
                    user_data = cur.fetchone()
                    if user_data:
                        return Usuario(
                            id=user_data['id'],
                            username=user_data['username'],
                            email=user_data['email'],
                            password_hash=user_data['password_hash'],
                            criado_em=user_data['criado_em'],
                            ativo=user_data['ativo']
                        )
        except Exception as e:
            print(f"Erro ao buscar usuário por ID: {e}")
        return None

    @staticmethod
    def get_by_username(username):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, username, email, password_hash, criado_em, ativo 
                        FROM usuario 
                        WHERE username = %s AND ativo = true
                    """, (username,))
                    user_data = cur.fetchone()
                    if user_data:
                        return Usuario(
                            id=user_data['id'],
                            username=user_data['username'],
                            email=user_data['email'],
                            password_hash=user_data['password_hash'],
                            criado_em=user_data['criado_em'],
                            ativo=user_data['ativo']
                        )
        except Exception as e:
            print(f"Erro ao buscar usuário por username: {e}")
        return None

    @staticmethod
    def create_user(username, password, email=None):
        try:
            password_hash = generate_password_hash(password)
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if email:
                        cur.execute("""
                            INSERT INTO usuario (username, email, password_hash) 
                            VALUES (%s, %s, %s) 
                            RETURNING id, username, email, password_hash, criado_em, ativo
                        """, (username, email, password_hash))
                    else:
                        cur.execute("""
                            INSERT INTO usuario (username, password_hash) 
                            VALUES (%s, %s) 
                            RETURNING id, username, email, password_hash, criado_em, ativo
                        """, (username, password_hash))
                    
                    conn.commit()
                    user_data = cur.fetchone()
                    
                    return Usuario(
                        id=user_data['id'],
                        username=user_data['username'],
                        email=user_data['email'],
                        password_hash=user_data['password_hash'],
                        criado_em=user_data['criado_em'],
                        ativo=user_data['ativo']
                    )
        except psycopg2.IntegrityError as e:
            raise Exception("Usuário ou email já existe")
        except Exception as e:
            raise Exception(f"Erro ao criar usuário: {e}")
