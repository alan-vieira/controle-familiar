# routes/auth.py
import psycopg2
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
import re
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

def is_valid_username(username):
    return re.match(r"^[a-zA-Z0-9_-]{3,30}$", username) is not None

# ─── REGISTRO ─────────────────────────────────────────────
@auth_bp.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados JSON inválidos'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username e senha são obrigatórios'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username deve ter pelo menos 3 caracteres'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400

    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(password)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO usuario (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (username, email if email else None, password_hash))
                user_id = cur.fetchone()[0]
                conn.commit()
            except psycopg2.IntegrityError as e:
                if 'username' in str(e):
                    return jsonify({'error': 'Username já existe'}), 409
                elif 'email' in str(e):
                    return jsonify({'error': 'E-mail já cadastrado'}), 409
                else:
                    raise
            except Exception as e:
                logger.error(f"Erro ao registrar usuário: {e}")
                return jsonify({'error': 'Erro interno ao criar conta'}), 500

    return jsonify({
        'message': 'Usuário criado com sucesso',
        'user_id': user_id
    }), 201

# ─── LOGIN ───────────────────────────────────────────────
@auth_bp.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400

    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM usuario WHERE username = %s", (username,))
            user = cur.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                access_token = create_access_token(
                    identity=str(user['id']),
                    additional_claims={'username': user['username']}
                )
                return jsonify({
                    'access_token': access_token,
                    'user_id': user['id'],
                    'username': user['username']
                }), 200

    return jsonify({'error': 'Credenciais inválidas'}), 401

# ─── STATUS (VERIFICAR SE LOGADO) ────────────────────────
@auth_bp.route('/auth/status', methods=['GET'])
@jwt_required()
def auth_status():
    current_user_id = get_jwt_identity()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, username FROM usuario WHERE id = %s", (current_user_id,))
            user = cur.fetchone()
            if user:
                return jsonify({
                    'logged_in': True,
                    'user_id': user['id'],
                    'username': user['username']
                })
    return jsonify({'logged_in': False}), 401

# ─── LOGOUT ──────────────────────────────────────────────
@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout bem-sucedido'}), 200
