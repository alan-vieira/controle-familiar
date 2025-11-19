from flask_login import UserMixin
from werkzeug.security import check_password_hash
from connection import get_db_connection

class Usuario(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user:
            return Usuario(user['id'], user['username'], user['password_hash'])
        return None

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user:
            return Usuario(user['id'], user['username'], user['password_hash'])
        return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
