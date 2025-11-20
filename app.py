import os
from flask_cors import CORS
from flask import Flask, request, jsonify, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from routes.colaboradores import colaboradores_bp
from routes.despesas import despesas_bp
from routes.rendas import rendas_bp
from routes.resumo import resumo_bp
from routes.divisao import divisao_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
    
    # CONFIGURAÇÃO CRUCIAL PARA SESSÕES ENTRE DOMÍNIOS
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True
    )

    # CORS com credenciais - IMPORTANTE para Vercel + Render
    CORS(
        app,
        origins=[
            "https://controle-familiar-frontend.vercel.app",
            "http://localhost:3000"  # Para desenvolvimento
        ],
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Configuração do Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from models import Usuario
        return Usuario.get_by_id(int(user_id))

    # Registrar blueprints
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')

    # --- PROTEGER TODAS AS ROTAS DA API ---
    @app.before_request
    def proteger_rotas_api():
        # Não proteger rotas públicas
        public_routes = ['login', 'auth_status', 'health', 'static']
        if request.endpoint in public_routes:
            return
        
        # Proteger todas as rotas /api/* (exceto login e auth_status)
        if request.path.startswith('/api/'):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Não autorizado. Faça login.'}), 401

    # Rota para a página inicial
    @app.route('/')
    def index():
        return redirect('https://controle-familiar-frontend.vercel.app')

    # Rota de login
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados JSON necessários'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username e password são obrigatórios'}), 400
        
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

    # Rota para logout
    @app.route('/api/logout', methods=['POST', 'OPTIONS'])
    def logout():
        if request.method == 'OPTIONS':
            return '', 200
        logout_user()
        return jsonify({'message': 'Logout bem-sucedido'}), 200

    # Rota para verificar status de login
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

    # Rota de saúde para o Render
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'OK', 'service': 'controle-familiar-api'}), 200

    # Rota para criar usuário admin inicial (REMOVER EM PRODUÇÃO APÓS USO)
    @app.route('/api/create-admin', methods=['POST'])
    def create_admin():
        from models import Usuario
        try:
            user = Usuario.create_user('admin', 'admin123', 'admin@familia.com')
            return jsonify({'message': 'Usuário admin criado'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    return app

# Função WSGI para Gunicorn
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
