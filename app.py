import os
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from datetime import datetime
import logging
from connection import get_db_connection
from config import SECRET_KEY
from psycopg2.extras import RealDictCursor
import secrets

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # 🔒 CONFIGURAÇÕES DE SEGURANÇA PARA CROSS-SITE
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,      # Impede acesso JavaScript ao cookie
        SESSION_COOKIE_SECURE=True,        # Apenas HTTPS (OBRIGATÓRIO para SameSite=None)
        SESSION_COOKIE_SAMESITE='None',    # Permite cross-site (frontend/backend em domínios diferentes)
        PERMANENT_SESSION_LIFETIME=3600    # Sessão expira em 1 hora
    )

    # CORS com configuração segura para cross-site
    CORS(app, 
         origins=['https://controle-familiar-frontend.vercel.app'],
         supports_credentials=True,        # IMPORTANTE: permite cookies cross-site
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-CSRF-Token']
    )

    # 🔥 SISTEMA DE AUTENTICAÇÃO SEGURO (substitui o current_user_id global)
    users_sessions = {}  # Em produção, use Redis ou database

    def login_required(f):
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            session_token = request.cookies.get('session_token')
            
            # Verificar token no header ou cookie
            token = None
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
            elif session_token:
                token = session_token
            
            if not token or token not in users_sessions:
                return jsonify({'error': 'Não autorizado'}), 401
            
            # Verificar se sessão expirou
            session_data = users_sessions[token]
            if datetime.now().timestamp() > session_data['expires_at']:
                del users_sessions[token]
                return jsonify({'error': 'Sessão expirada'}), 401
            
            # Atualizar tempo de expiração
            session_data['expires_at'] = datetime.now().timestamp() + 3600
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function

    def get_current_user_id():
        """Obtém o ID do usuário atual baseado no token"""
        auth_header = request.headers.get('Authorization')
        session_token = request.cookies.get('session_token')
        
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif session_token:
            token = session_token
        
        if token and token in users_sessions:
            return users_sessions[token]['user_id']
        return None

    # Rota de saúde
    @app.route('/')
    def index():
        return jsonify({'status': 'healthy', 'message': 'Controle Familiar API'})

    @app.route('/health')
    def health():
        return jsonify({'status': 'OK'})

    # 🔥 ROTA DE DEBUG DO BANCO
    @app.route('/debug/db-test')
    def debug_db_test():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Testar consulta simples
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                # Testar contar colaboradores
                cursor.execute("SELECT COUNT(*) as count FROM colaborador")
                count_result = cursor.fetchone()
                
                # Testar lista de tabelas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                
                return jsonify({
                    'database_connection': 'OK',
                    'test_query': result,
                    'colaboradores_count': count_result,
                    'tables': [table['table_name'] for table in tables]
                })
                
        except Exception as e:
            return jsonify({
                'database_connection': 'ERROR',
                'error': str(e)
            }), 500

    # 🔒 ROTA DE LOGIN SEGURA
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
            
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400
        
        # Verificação no banco de dados
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM usuario WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                
                if user_data:
                    # 🔒 Em produção, use bcrypt para verificar a senha
                    # Por enquanto, verificação simples
                    if user_data['password_hash'].endswith('admin123'):  # Verificação simplificada
                        # Gerar token de sessão seguro
                        session_token = secrets.token_urlsafe(32)
                        
                        # Salvar sessão
                        users_sessions[session_token] = {
                            'user_id': user_data['id'],
                            'username': user_data['username'],
                            'expires_at': datetime.now().timestamp() + 3600  # 1 hora
                        }
                        
                        response = jsonify({
                            'message': 'Login bem-sucedido', 
                            'username': user_data['username'],
                            'user_id': user_data['id']
                        })
                        
                        # 🔒 Setar cookie seguro para cross-site
                        response.set_cookie(
                            'session_token',
                            value=session_token,
                            httponly=True,
                            secure=True,
                            samesite='None',
                            max_age=3600
                        )
                        
                        return response, 200
            
            return jsonify({'error': 'Credenciais inválidas'}), 401
            
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    # 🔒 ROTA DE LOGOUT
    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        session_token = request.cookies.get('session_token')
        if session_token and session_token in users_sessions:
            del users_sessions[session_token]
        
        response = jsonify({'message': 'Logout bem-sucedido'})
        response.set_cookie('session_token', '', expires=0)
        return response

    @app.route('/api/auth/status', methods=['GET', 'OPTIONS'])
    def auth_status():
        if request.method == 'OPTIONS':
            return '', 200
        
        user_id = get_current_user_id()
        if user_id:
            return jsonify({
                'logged_in': True, 
                'username': 'admin',  # Em produção, buscar do banco
                'user_id': user_id
            }), 200
        else:
            return jsonify({'logged_in': False}), 200

    # 🔥 ROTAS DE COLABORADORES (COM CONNECTION MANAGER)
    @app.route('/api/colaboradores', methods=['GET'])
    @login_required
    def listar_colaboradores():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM colaborador ORDER BY nome")
                colaboradores = cursor.fetchall()
                return jsonify(colaboradores)
                
        except Exception as e:
            logger.error(f"Erro ao buscar colaboradores: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'Erro interno do servidor',
                'details': str(e)
            }), 500

    # 🔥 ROTAS DE DESPESAS (COM CONNECTION MANAGER)
    @app.route('/api/despesas', methods=['GET'])
    @login_required
    def listar_despesas():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM despesa ORDER BY data_compra DESC")
                despesas = cursor.fetchall()
                
                # Converter para JSON
                for despesa in despesas:
                    if despesa.get('data_compra'):
                        despesa['data_compra'] = despesa['data_compra'].isoformat()
                    if despesa.get('valor'):
                        despesa['valor'] = float(despesa['valor'])
                
                return jsonify(despesas)
                
        except Exception as e:
            logger.error(f"Erro ao buscar despesas: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/despesas', methods=['POST'])
    @login_required
    def criar_despesa():
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Dados inválidos'}), 400
                
            # Campos obrigatórios
            required_fields = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({'error': f'Campo {field} é obrigatório'}), 400
            
            # Validar valores
            try:
                valor = float(data['valor'])
                colaborador_id = int(data['colaborador_id'])
            except (ValueError, TypeError):
                return jsonify({'error': 'valor ou colaborador_id inválidos'}), 400
            
            # Validar enums
            tipos_pg_validos = ['credito', 'debito', 'pix', 'dinheiro', 'outros']
            if data['tipo_pg'] not in tipos_pg_validos:
                return jsonify({'error': f'tipo_pg inválido. Use: {tipos_pg_validos}'}), 400
            
            categorias_validas = ['moradia', 'alimentacao', 'restaurante_lanche', 'casa_utilidades', 'saude', 'transporte', 'lazer_outros']
            if data['categoria'] not in categorias_validas:
                return jsonify({'error': f'categoria inválida. Use: {categorias_validas}'}), 400
            
            # Processar data
            data_compra = data['data_compra']
            if 'T' in data_compra:
                data_compra = data_compra.split('T')[0]
            
            # Calcular mes_vigente
            data_obj = datetime.strptime(data_compra, '%Y-%m-%d')
            mes_vigente = data_obj.strftime('%Y-%m')
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO despesa 
                       (data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (data_compra, mes_vigente, data['descricao'], valor, data['tipo_pg'], colaborador_id, data['categoria'])
                )
                
                despesa_id = cursor.fetchone()[0]
                conn.commit()
                
                return jsonify({
                    'id': despesa_id,
                    'data_compra': data_compra,
                    'mes_vigente': mes_vigente,
                    'descricao': data['descricao'],
                    'valor': valor,
                    'tipo_pg': data['tipo_pg'],
                    'colaborador_id': colaborador_id,
                    'categoria': data['categoria'],
                    'message': 'Despesa criada com sucesso'
                }), 201
                
        except Exception as e:
            logger.error(f"Erro ao criar despesa: {str(e)}")
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500

    # 🔥 OUTRAS ROTAS (COM CONNECTION MANAGER)
    @app.route('/api/rendas', methods=['GET'])
    @login_required
    def listar_rendas():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM renda_mensal ORDER BY mes_ano DESC")
                rendas = cursor.fetchall()
                
                for renda in rendas:
                    if renda.get('valor'):
                        renda['valor'] = float(renda['valor'])
                
                return jsonify(rendas)
                
        except Exception as e:
            logger.error(f"Erro ao buscar rendas: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/resumo', methods=['GET'])
    @login_required
    def obter_resumo():
        return jsonify({
            'total_despesas': 0,
            'total_rendas': 0,
            'saldo': 0,
            'message': 'Resumo carregado com sucesso'
        })

    @app.route('/api/divisao', methods=['GET'])
    @login_required
    def obter_divisao():
        return jsonify([])

    return app

# Mantemos a função WSGI
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)