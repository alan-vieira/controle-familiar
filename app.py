import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from flask_login import LoginManager, current_user
from routes.auth import auth_bp
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

    # Configuração do Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Atualizado para usar o blueprint

    @login_manager.user_loader
    def load_user(user_id):
        from models import Usuario
        return Usuario.get_by_id(int(user_id))

    # Registrar blueprints - INCLUINDO auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')

    # 🔥 MIDDLEWARE SIMPLIFICADO
    @app.before_request
    def proteger_rotas():
        # Rotas públicas (apenas as essenciais)
        public_routes = ['/api/login', '/api/auth/status', '/api/logout', '/health', '/']
        if request.path in public_routes:
            return
        
        # Protege apenas se for API e não estiver autenticado
        if request.path.startswith('/api/') and not current_user.is_authenticated:
            return jsonify({'error': 'Não autorizado'}), 401

    # ROTAS BÁSICAS
    @app.route('/')
    def index():
        return redirect('https://controle-familiar-frontend.vercel.app')

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