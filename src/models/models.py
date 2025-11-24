import bcrypt
from flask_login import UserMixin
from src.models.database import get_db_connection
from werkzeug.security import check_password_hash

class Usuario(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password = password_hash

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, email, password_hash FROM usuario WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                # Já é um RealDictRow (já é dicionário), não precisa converter!
                print(f"🔍 DEBUG GET_BY_ID - User dict: {dict(user)}")
                print(f"🔍 DEBUG GET_BY_ID - Password hash value: {user['password_hash']}")
                
                return Usuario(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    password_hash=user['password_hash']  # ACESSA DIRETAMENTE
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
                # Já é um RealDictRow (já é dicionário), não precisa converter!
                print(f"🔍 DEBUG GET_BY_USERNAME - User dict: {dict(user)}")
                print(f"🔍 DEBUG GET_BY_USERNAME - Password hash value: {user['password_hash']}")
                
                return Usuario(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    password_hash=user['password_hash']  # ACESSA DIRETAMENTE
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
            print(f"🔍 DEBUG CHECK_PASSWORD - Self.password: {self.password}")
            print(f"🔍 DEBUG CHECK_PASSWORD - Password to check: {password}")
            
            # Usar check_password_hash do Werkzeug que suporta scrypt
            result = check_password_hash(self.password, password)
            print(f"🔍 DEBUG CHECK_PASSWORD - Result: {result}")
            return result
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
            
            # Fazer hash da senha com werkzeug (compatível com scrypt)
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
