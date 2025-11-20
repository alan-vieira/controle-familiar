import bcrypt
from flask_login import UserMixin
from database import get_db_connection

class Usuario(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password = password_hash  # Mapeia password_hash para password para o Flask-Login

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, email, password_hash FROM usuario WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                # Converter tupla para dicionário
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                return Usuario(
                    id=user_dict['id'],
                    username=user_dict['username'],
                    email=user_dict['email'],
                    password_hash=user_dict['password_hash']
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário por ID: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, email, password_hash FROM usuario WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                # Converter tupla para dicionário
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                return Usuario(
                    id=user_dict['id'],
                    username=user_dict['username'],
                    email=user_dict['email'],
                    password_hash=user_dict['password_hash']
                )
            return None
        except Exception as e:
            print(f"Erro ao buscar usuário por username: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def check_password(self, password):
        try:
            # O hash no banco foi gerado com werkzeug, não bcrypt!
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password, password)
        except Exception as e:
            print(f"Erro ao verificar senha: {e}")
            return False

    @staticmethod
    def create_user(username, password, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Verificar se usuário já existe
            cursor.execute("SELECT id FROM usuario WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                raise Exception("Usuário ou email já existe")
            
            # Fazer hash da senha com werkzeug (compatível com o admin existente)
            from werkzeug.security import generate_password_hash
            hashed_password = generate_password_hash(password)
            
            # Inserir novo usuário
            cursor.execute(
                "INSERT INTO usuario (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (username, email, hashed_password)
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            return Usuario(user_id, username, email, hashed_password)
        except Exception as e:
            conn.rollback()
            print(f"Erro ao criar usuário: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()
