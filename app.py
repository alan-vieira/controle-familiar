import os
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
    app = Flask(__name__, static_folder='frontend')
    app.config['SECRET_KEY'] = SECRET_KEY

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
        if current_user.is_authenticated:
            return app.send_static_file('index.html')
        else:
            return redirect(url_for('login'))

    # Rota para a página de login
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            user = Usuario.get_by_username(username)
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                return jsonify({'error': 'Credenciais inválidas'}), 401

        return app.send_static_file('index.html')

    # Rota para logout
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

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
