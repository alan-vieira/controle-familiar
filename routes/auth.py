from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user
from models import Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = Usuario.get_by_username(username)
    
    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify({
            'message': 'Login bem-sucedido', 
            'username': user.username,
            'user_id': user.id
        }), 200
    else:
        return jsonify({'error': 'Credenciais inválidas'}), 401

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    if request.method == 'OPTIONS':
        return '', 200
    logout_user()
    return jsonify({'message': 'Logout bem-sucedido'}), 200

@auth_bp.route('/auth/status', methods=['GET', 'OPTIONS'])
def auth_status():
    if request.method == 'OPTIONS':
        return '', 200
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True, 
            'username': current_user.username,
            'user_id': current_user.id
        }), 200
    else:
        return jsonify({'logged_in': False}), 200