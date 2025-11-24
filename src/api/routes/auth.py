from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from src.models.models import Usuario
from src.models.connection import get_db_connection
from werkzeug.security import check_password_hash
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400
        
        # Buscar usuário no banco de dados
        with get_db_connection() as conn:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM usuario WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            
            if user_data:
                if check_password_hash(user_data['password_hash'], password):
                    access_token = create_access_token(
                        identity=str(user_data['id']),
                        additional_claims={
                            'username': user_data['username'],
                            'email': user_data.get('email', '')
                        }
                    )
                    
                    return jsonify({
                        'message': 'Login bem-sucedido',
                        'access_token': access_token,
                        'user_id': user_data['id'],
                        'username': user_data['username']
                    }), 200
            
            return jsonify({'error': 'Credenciais inválidas'}), 401
            
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return '', 200
    # Com JWT, o logout é geralmente feito no frontend invalidando o token
    # Aqui apenas retornamos uma mensagem de sucesso
    return jsonify({'message': 'Logout bem-sucedido'}), 200

@auth_bp.route('/auth/status', methods=['GET'])
@jwt_required()
def auth_status():
    try:
        current_user_id = get_jwt_identity()
        
        with get_db_connection() as conn:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, username, email FROM usuario WHERE id = %s", (current_user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                return jsonify({
                    'logged_in': True,
                    'user_id': user_data['id'],
                    'username': user_data['username'],
                    'email': user_data['email']
                })
            else:
                return jsonify({'logged_in': False}), 401
                
    except Exception as e:
        logger.error(f"Erro no status: {e}")
        return jsonify({'logged_in': False}), 401