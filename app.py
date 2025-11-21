import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging
from connection import get_db_connection
from config import SECRET_KEY
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # 🔐 CONFIGURAÇÃO JWT
    app.config['JWT_SECRET_KEY'] = SECRET_KEY  # Usa a mesma SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # 🔒 CONFIGURAÇÕES DE SEGURANÇA
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None',
    )

    # CORS com configuração segura
    CORS(app, 
         origins=['https://controle-familiar-frontend.vercel.app'],
         supports_credentials=True,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization']
    )

    # Inicializar JWT
    jwt = JWTManager(app)

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
                
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) as count FROM colaborador")
                count_result = cursor.fetchone()
                
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

    # 🔐 ROTA DE LOGIN COM JWT
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Dados não fornecidos'}), 400
                
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400
            
            # Verificação no banco de dados
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM usuario WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                
                if user_data:
                    # Verificar senha com werkzeug
                    if check_password_hash(user_data['password_hash'], password):
                        # ✅ CORREÇÃO: Garantir que identity seja string
                        access_token = create_access_token(
                            identity=str(user_data['id']),  # ← CONVERTER PARA STRING
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

    # 🔐 ROTA DE LOGOUT
    @app.route('/api/logout', methods=['POST'])
    @jwt_required()
    def logout():
        # JWT é stateless, então basta o frontend descartar o token
        return jsonify({'message': 'Logout bem-sucedido'})

    # 🔐 STATUS DE AUTENTICAÇÃO
    @app.route('/api/auth/status', methods=['GET'])
    @jwt_required()
    def auth_status():
        try:
            current_user_id = get_jwt_identity()
            
            with get_db_connection() as conn:
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

    # 🔥 ROTAS DE COLABORADORES (PROTEGIDAS COM JWT)
    @app.route('/api/colaboradores', methods=['GET'])
    @jwt_required()
    def listar_colaboradores():
        try:
            current_user_id = get_jwt_identity()
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # ✅ CORREÇÃO: Filtrar por usuário logado
                cursor.execute("""
                    SELECT c.*, u.username as usuario_nome 
                    FROM colaborador c 
                    LEFT JOIN usuario u ON c.usuario_id = u.id 
                    WHERE c.usuario_id = %s 
                    ORDER BY c.nome
                """, (current_user_id,))
                
                colaboradores = cursor.fetchall()
                return jsonify(colaboradores)
                
        except Exception as e:
            logger.error(f"Erro ao buscar colaboradores: {str(e)}", exc_info=True)
            return jsonify({'error': 'Erro interno do servidor'}), 500

    # 🔥 ROTAS DE DESPESAS (PROTEGIDAS COM JWT)
    @app.route('/api/despesas', methods=['GET'])
    @jwt_required()
    def listar_despesas():
        try:
            current_user_id = get_jwt_identity()
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # ✅ CORREÇÃO: Filtrar por usuário logado
                cursor.execute("""
                    SELECT d.*, c.nome as colaborador_nome 
                    FROM despesa d 
                    LEFT JOIN colaborador c ON d.colaborador_id = c.id 
                    WHERE c.usuario_id = %s 
                    ORDER BY d.data_compra DESC
                """, (current_user_id,))
                
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
    @jwt_required()
    def criar_despesa():
        try:
            current_user_id = get_jwt_identity()
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
            
            # ✅ CORREÇÃO: Verificar se colaborador pertence ao usuário
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT id FROM colaborador WHERE id = %s AND usuario_id = %s", 
                             (colaborador_id, current_user_id))
                colaborador_valido = cursor.fetchone()
                
                if not colaborador_valido:
                    return jsonify({'error': 'Colaborador não encontrado ou não pertence ao usuário'}), 400
            
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

    # 🔥 OUTRAS ROTAS (PROTEGIDAS COM JWT)
    @app.route('/api/rendas', methods=['GET'])
    @jwt_required()
    def listar_rendas():
        try:
            current_user_id = get_jwt_identity()
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # ✅ CORREÇÃO: Filtrar por usuário logado
                cursor.execute("""
                    SELECT r.* 
                    FROM renda_mensal r 
                    WHERE r.usuario_id = %s 
                    ORDER BY r.mes_ano DESC
                """, (current_user_id,))
                
                rendas = cursor.fetchall()
                
                for renda in rendas:
                    if renda.get('valor'):
                        renda['valor'] = float(renda['valor'])
                
                return jsonify(rendas)
                
        except Exception as e:
            logger.error(f"Erro ao buscar rendas: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/resumo', methods=['GET'])
    @jwt_required()
    def obter_resumo():
        try:
            current_user_id = get_jwt_identity()
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Total despesas
                cursor.execute("""
                    SELECT COALESCE(SUM(d.valor), 0) as total_despesas
                    FROM despesa d
                    JOIN colaborador c ON d.colaborador_id = c.id
                    WHERE c.usuario_id = %s
                """, (current_user_id,))
                total_despesas = cursor.fetchone()['total_despesas'] or 0
                
                # Total rendas
                cursor.execute("""
                    SELECT COALESCE(SUM(valor), 0) as total_rendas
                    FROM renda_mensal 
                    WHERE usuario_id = %s
                """, (current_user_id,))
                total_rendas = cursor.fetchone()['total_rendas'] or 0
                
                saldo = total_rendas - total_despesas
                
                return jsonify({
                    'total_despesas': float(total_despesas),
                    'total_rendas': float(total_rendas),
                    'saldo': float(saldo),
                    'message': 'Resumo carregado com sucesso'
                })
                
        except Exception as e:
            logger.error(f"Erro ao buscar resumo: {str(e)}")
            return jsonify({
                'total_despesas': 0,
                'total_rendas': 0,
                'saldo': 0,
                'error': 'Erro ao calcular resumo'
            }), 500

    @app.route('/api/divisao', methods=['GET'])
    @jwt_required()
    def obter_divisao():
        return jsonify([])

    return app

# Função WSGI mantida
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)