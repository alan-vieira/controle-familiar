# blueprints/auth.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    if not 
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

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout bem-sucedido'}), 200