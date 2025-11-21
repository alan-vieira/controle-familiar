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
    
    # CONFIGURAÇÃO CRUCIAL PARA SESSÕES ENTRE DOMÍNIOS - CORRIGIDA!
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",  # ← "None" para cross-domain
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
        # Lista de rotas públicas (por path, mais confiável que endpoint)
        public_paths = [
            '/api/login',
            '/api/auth/status',
            '/api/logout',
            '/api/create-admin',
            '/api/init-db',
            '/api/debug-hash',
            '/api/reset-admin',
            '/health',
            '/'
        ]
        
        # DEBUG: Mostrar qual path está sendo acessado
        print(f"🔍 Path acessado: {request.path}")
        
        # Se a rota atual está na lista de públicas, não proteger
        if request.path in public_paths:
            print(f"✅ Rota pública, permitindo acesso: {request.path}")
            return
        
        # Proteger todas as outras rotas /api/*
        if request.path.startswith('/api/'):
            if not current_user.is_authenticated:
                print(f"🚫 Rota protegida, usuário não autenticado: {request.path}")
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
            
        try:
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
                print(f"✅ USUÁRIO LOGADO: {user.username} (ID: {user.id})")
                return jsonify({
                    'message': 'Login bem-sucedido', 
                    'username': user.username,
                    'user_id': user.id
                }), 200
            else:
                return jsonify({'error': 'Credenciais inválidas'}), 401
                
        except Exception as e:
            print(f"❌ ERRO NO LOGIN: {str(e)}")
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500

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

    # Rota para debug do hash (REMOVER EM PRODUÇÃO)
    @app.route('/api/debug-hash', methods=['GET'])
    def debug_hash():
        try:
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash FROM usuario WHERE username = 'admin'")
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return jsonify({
                'username': user['username'],
                'password_hash': user['password_hash']
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Rota para resetar senha do admin (REMOVER EM PRODUÇÃO)
    @app.route('/api/reset-admin', methods=['POST'])
    def reset_admin():
        try:
            from database import get_db_connection
            from werkzeug.security import generate_password_hash
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Deletar admin existente
            cursor.execute("DELETE FROM usuario WHERE username = 'admin'")
            
            # Recriar admin com senha conhecida
            hashed_password = generate_password_hash('admin123')
            
            cursor.execute(
                "INSERT INTO usuario (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                ('admin', 'admin@familia.com', hashed_password)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({'message': 'Admin resetado com senha: admin123'}), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

# Função WSGI para Gunicorn
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
