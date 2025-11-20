import bcrypt
from flask_login import UserMixin
from database import get_db_connection

class Usuario(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, email, password FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                # Converter tupla para dicionário
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                return Usuario(
                    id=user_dict['id'],
                    username=user_dict['username'],
                    email=user_dict['email'],
                    password=user_dict['password']
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
            cursor.execute("SELECT id, username, email, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                # Converter tupla para dicionário
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, user))
                return Usuario(
                    id=user_dict['id'],
                    username=user_dict['username'],
                    email=user_dict['email'],
                    password=user_dict['password']
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
            # Verificar se a senha fornecida corresponde ao hash armazenado
            return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
        except Exception as e:
            print(f"Erro ao verificar senha: {e}")
            return False

    @staticmethod
    def create_user(username, password, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Verificar se usuário já existe
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                raise Exception("Usuário ou email já existe")
            
            # Fazer hash da senha
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Inserir novo usuário
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
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
