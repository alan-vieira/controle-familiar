import os
from flask_cors import CORS
from flask import Flask, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from routes.colaboradores import colaboradores_bp
from routes.despesas import despesas_bp
from routes.rendas import rendas_bp
from routes.resumo import resumo_bp
from routes.divisao import divisao_bp
from config import SECRET_KEY
from models import Usuario
from connection import get_db_connection

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY

    # CONFIGURAÇÃO CRUCIAL PARA SESSÕES ENTRE DOMÍNIOS
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_NAME="session"
    )

    # CORS com credenciais
    CORS(
        app,
        origins=["https://controle-familiar-frontend.vercel.app"],
        supports_credentials=True
    )


    # Configuração do Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.get(int(user_id))

    # Registrar blueprints
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')

    # --- PROTEGER TODAS AS ROTAS DA API ---
    @app.before_request
    def proteger_rotas_api():
        if request.endpoint and request.blueprint in ['colaboradores', 'despesas', 'rendas', 'resumo', 'divisao']:
            if not current_user.is_authenticated:
                return jsonify({'error': 'Não autorizado. Faça login.'}), 401

    # Rota para a página inicial
    @app.route('/')
    def index():
        return redirect('https://controle-familiar-frontend.vercel.app')  # Redireciona para Vercel

    # Rota para a página de login
    @app.route('/api/login', methods=['POST'])  # Mude para /api/login e POST apenas
    def login():
        data = request.get_json()  # Aceita JSON em vez de form
        username = data.get('username')
        password = data.get('password')
        user = Usuario.get_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            return jsonify({'message': 'Login bem-sucedido', 'username': user.username}), 200
        else:
            return jsonify({'error': 'Credenciais inválidas'}), 401


    # Rota para logout
    @app.route('/api/logout', methods=['POST'])
    def logout():
        logout_user()
        return jsonify({'message': 'Logout bem-sucedido'})

    # Rota para verificar o status de login (não deve ser protegida!)
    @app.route('/api/auth/status')
    def auth_status():
        if current_user.is_authenticated:
            return jsonify({'logged_in': True, 'username': current_user.username})
        else:
            return jsonify({'logged_in': False}), 401

    # Rota de saúde para o Render (não deve ser protegida!)
    @app.route('/health')
    def health():
        return {'status': 'OK'}, 200

    return app

# Função WSGI que o Gunicorn chama
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
