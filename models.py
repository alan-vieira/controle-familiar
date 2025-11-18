from flask_login import UserMixin
from werkzeug.security import check_password_hash
from connection import get_db_connection # Importar a função de conexão

class Usuario(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, password_hash FROM usuario WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    return Usuario(id=row[0], username=row[1], password_hash=row[2])
        return None

    @staticmethod
    def get_by_username(username):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, password_hash FROM usuario WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return Usuario(id=row[0], username=row[1], password_hash=row[2])
        return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
