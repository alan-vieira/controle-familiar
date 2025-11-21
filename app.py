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
    app.config['JWT_SECRET_KEY'] = SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # 🔒 CONFIGURAÇÕES DE SEGURANÇA
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='None',
    )

    # CORS
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
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM usuario WHERE username = %s", (username,))
                user_data = cursor.fetchone()
                
                if user_data:
                    if check_password_hash(user_data['password_hash'], password):
                        access_token = create_access_token(
                            identity=str(user_data['id']),
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

    # 🔥 ROTAS DE COLABORADORES - SEM FILTRO POR USUÁRIO
    @app.route('/api/colaboradores', methods=['GET'])
    @jwt_required()
    def listar_colaboradores():
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                    colabs = [dict(r) for r in cur.fetchall()]
                    return jsonify({"colaboradores": colabs})
        else:
            data = request.json
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                        (data['nome'], data['dia_fechamento'])
                    )
                    conn.commit()
                    return jsonify({"id": cur.fetchone()['id']}), 201

    # 🔥 ROTAS DE DESPESAS - SEM FILTRO POR USUÁRIO
    @app.route('/api/despesas', methods=['GET'])
    @jwt_required()
    def listar_despesas():
        if request.method == 'GET':
            mes = request.args.get('mes_vigente')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if mes:
                        cur.execute("""
                            SELECT d.*, c.nome AS colaborador_nome
                            FROM despesa d
                            JOIN colaborador c ON d.colaborador_id = c.id
                            WHERE d.mes_vigente = %s
                        """, (mes,))
                    else:
                        cur.execute("""
                            SELECT d.*, c.nome AS colaborador_nome
                            FROM despesa d
                            JOIN colaborador c ON d.colaborador_id = c.id
                        """)
                    rows = []
                    for r in cur.fetchall():
                        row = dict(r)
                        if row.get('data_compra'):
                            row['data_compra'] = row['data_compra'].strftime('%d/%m/%Y')
                        rows.append(row)
                    return jsonify(rows)
        else:
            data = request.json
            try:
                data_compra = datetime.strptime(data['data_compra'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Data inválida. Use YYYY-MM-DD."}), 400

            if data.get('valor', 0) <= 0:
                return jsonify({"error": "Valor deve ser maior que zero."}), 400

            tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
            colab_id = data['colaborador_id']
            categoria = data.get('categoria')

            if not categoria or categoria not in CATEGORIAS_VALIDAS:
                return jsonify({"error": "Categoria inválida ou ausente."}), 400

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                    colab = cur.fetchone()
                    if not colab:
                        return jsonify({"error": "Colaborador não encontrado"}), 400

                    mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])
                    cur.execute("""
                        INSERT INTO despesa (
                            data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria))
                    conn.commit()
                    result = cur.fetchone()
                    return jsonify({"id": result['id'], "mes_vigente": mes_vigente}), 201

    
    # 🔥 ROTAS DE RENDAS - SEM FILTRO POR USUÁRIO
    @app.route('/api/rendas', methods=['GET', 'POST'])
    @jwt_required()
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

    # 🔥 RESUMO - SEM FILTRO POR USUÁRIO
    @app.route('/resumo/<mes_ano>')
    @jwt_required()
    def obter_resumo(mes_ano):
        try:
            if not re.match(r'^\d{4}-\d{2}$', mes_ano):
                return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Total de despesas
                    cur.execute("SELECT COALESCE(SUM(valor), 0) AS total FROM despesa WHERE mes_vigente = %s", (mes_ano,))
                    total_despesas = float(cur.fetchone()['total'])

                    # Rendas por colaborador
                    cur.execute("""
                        SELECT c.id, c.nome, r.valor
                        FROM colaborador c
                        LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                        ORDER BY c.id
                    """, (mes_ano,))
                    rendas = []
                    for row in cur.fetchall():
                        valor = float(row['valor']) if row['valor'] is not None else None
                        rendas.append({
                            'id': row['id'],
                            'nome': row['nome'],
                            'valor': valor
                        })

                    # Verificar se todas as rendas estão preenchidas
                    for r in rendas:
                        if r['valor'] is None:
                            return jsonify({"error": f"Renda não registrada para {r['nome']} em {mes_ano}"}), 400

                    total_renda = sum(r['valor'] for r in rendas)
                    if total_renda == 0:
                        return jsonify({"error": "Renda total zero"}), 400

                    # Quanto cada um pagou em despesas
                    pagamentos = {}
                    for r in rendas:
                        cur.execute("""
                            SELECT COALESCE(SUM(valor), 0) AS total
                            FROM despesa
                            WHERE colaborador_id = %s AND mes_vigente = %s
                        """, (r['id'], mes_ano))
                        pagamentos[r['id']] = float(cur.fetchone()['total'])

                    # Montar resposta
                    resumo_data = {
                        "mes": mes_ano,
                        "total_despesas": round(total_despesas, 2),
                        "total_renda": round(total_renda, 2),
                        "colaboradores": []
                    }

                    for r in rendas:
                        perc = r['valor'] / total_renda
                        deve_pagar = total_despesas * perc
                        pagou = pagamentos[r['id']]
                        saldo = pagou - deve_pagar

                        resumo_data["colaboradores"].append({
                            "id": r['id'],
                            "nome": r['nome'],
                            "renda": round(r['valor'], 2),
                            "percentual": round(perc, 4),
                            "deve_pagar": round(deve_pagar, 2),
                            "pagou": round(pagou, 2),
                            "saldo": round(saldo, 2)
                        })

                    return jsonify(resumo_data)

        except Exception as e:
            print("❌ Erro no resumo:", str(e))
            return jsonify({"error": "Erro interno"}), 500
    
    # 🔐 LOGOUT
    @app.route('/api/logout', methods=['POST'])
    @jwt_required()
    def logout():
        return jsonify({'message': 'Logout bem-sucedido'})

    return app

# Função WSGI mantida
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)