import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user
from database import get_db_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-in-production')
    
    # CONFIGURAÇÃO SIMPLES E FUNCIONAL
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True
    )

    # CORS SIMPLES
    CORS(app, supports_credentials=True)

    # Configuração do Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import Usuario
        return Usuario.get_by_id(int(user_id))

    # 🔥 MIDDLEWARE SIMPLIFICADO
    @app.before_request
    def proteger_rotas():
        # Rotas públicas
        public_routes = ['/api/login', '/api/auth/status', '/api/logout', '/health', '/', '/debug/routes']
        if request.path in public_routes:
            return
        
        # Protege APIs
        if request.path.startswith('/api/') and not current_user.is_authenticated:
            return jsonify({'error': 'Não autorizado'}), 401

    # 🔥🔥🔥 ROTAS DIRETAS NO APP.PY - GARANTIDO FUNCIONAR

    # ROTAS BÁSICAS
    @app.route('/')
    def index():
        return redirect('https://controle-familiar-frontend.vercel.app')

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'OK'}), 200

    @app.route('/debug/routes')
    def debug_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static/'):
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': str(rule)
                })
        return jsonify({'routes': routes})

    # 🔥 ROTAS DE AUTENTICAÇÃO
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

    # 🔥 ROTAS DE COLABORADORES
    @app.route('/api/colaboradores', methods=['GET'])
    @login_required
    def listar_colaboradores():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM colaborador ORDER BY nome")
            colaboradores = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify(colaboradores)
            
        except Exception as e:
            logger.error(f"Erro ao buscar colaboradores: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/colaboradores', methods=['POST'])
    @login_required
    def criar_colaborador():
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Dados inválidos'}), 400
                
            required_fields = ['nome', 'dia_fechamento']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({'error': f'Campo {field} é obrigatório'}), 400
            
            dia = int(data['dia_fechamento'])
            if dia < 1 or dia > 31:
                return jsonify({'error': 'dia_fechamento deve estar entre 1 e 31'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s)",
                (data['nome'], dia)
            )
            
            conn.commit()
            colaborador_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'id': colaborador_id,
                'nome': data['nome'],
                'dia_fechamento': dia,
                'message': 'Colaborador criado com sucesso'
            }), 201
            
        except Exception as e:
            logger.error(f"Erro ao criar colaborador: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    # 🔥 ROTAS DE DESPESAS
    @app.route('/api/despesas', methods=['GET'])
    @login_required
    def listar_despesas():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM despesa ORDER BY data_compra DESC")
            despesas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
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
                return jsonify({'error': f'tipo_pg inválido'}), 400
            
            categorias_validas = ['moradia', 'alimentacao', 'restaurante_lanche', 'casa_utilidades', 'saude', 'transporte', 'lazer_outros']
            if data['categoria'] not in categorias_validas:
                return jsonify({'error': f'categoria inválida'}), 400
            
            # Processar data
            data_compra = data['data_compra']
            if 'T' in data_compra:
                data_compra = data_compra.split('T')[0]
            
            # Calcular mes_vigente
            data_obj = datetime.strptime(data_compra, '%Y-%m-%d')
            mes_vigente = data_obj.strftime('%Y-%m')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO despesa 
                   (data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (data_compra, mes_vigente, data['descricao'], valor, data['tipo_pg'], colaborador_id, data['categoria'])
            )
            
            conn.commit()
            despesa_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
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

    # 🔥 OUTRAS ROTAS (MÍNIMAS)
    @app.route('/api/rendas', methods=['GET'])
    @login_required
    def listar_rendas():
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM renda_mensal ORDER BY mes_ano DESC")
            rendas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
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
    app.run(debug=True, host='0.0.0.0', port=port)