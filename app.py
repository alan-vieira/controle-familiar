import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user
from routes.colaboradores import colaboradores_bp
from routes.despesas import despesas_bp
from routes.rendas import rendas_bp
from routes.resumo import resumo_bp
from routes.divisao import divisao_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
    
    # CONFIGURAÇÃO SIMPLES E FUNCIONAL
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True
    )

    # CORS SIMPLES - como no protótipo, mas com credenciais
    CORS(app, supports_credentials=True)

    # Configuração do Flask-Login (mantemos porque funciona)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import Usuario
        return Usuario.get_by_id(int(user_id))

    # Registrar blueprints - SIMPLES como no protótipo
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')

    # 🔥 MIDDLEWARE SIMPLIFICADO - apenas o essencial
    @app.before_request
    def proteger_rotas():
        # Rotas públicas (apenas as essenciais)
        if request.path in ['/api/login', '/api/auth/status', '/api/logout', '/health', '/']:
            return
        
        # Protege apenas se for API e não estiver autenticado
        if request.path.startswith('/api/') and not current_user.is_authenticated:
            return jsonify({'error': 'Não autorizado'}), 401

    # ROTAS ESSENCIAIS - mantemos o que funciona
    @app.route('/')
    def index():
        return redirect('https://controle-familiar-frontend.vercel.app')

    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
            
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        from models import Usuario
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

    @app.route('/api/logout', methods=['POST', 'OPTIONS'])
    def logout():
        if request.method == 'OPTIONS':
            return '', 200
        logout_user()
        return jsonify({'message': 'Logout bem-sucedido'}), 200

    @app.route('/api/auth/status', methods=['GET', 'OPTIONS'])
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

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'OK'}), 200

    return app

# Mantemos a função WSGI para o Render
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
