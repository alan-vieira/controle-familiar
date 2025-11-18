# scripts/create_admin_user.py
from werkzeug.security import generate_password_hash
from connection import get_db_connection

def create_admin_user(username, password):
    password_hash = generate_password_hash(password)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO usuario (username, password_hash) VALUES (%s, %s)",
                    (username, password_hash)
                )
                conn.commit()
                print(f"Usuário '{username}' criado com sucesso!")
            except Exception as e:
                print(f"Erro ao criar usuário: {e}")
                conn.rollback()

if __name__ == "__main__":
    # Substitua 'admin' e 'senha_segura' pelos valores desejados
    create_admin_user('admin', 'senha_segura')
