import os
import re
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

# Valores válidos de categoria (alinhados com o schema.sql)
CATEGORIAS_VALIDAS = {
    'moradia',
    'alimentacao',
    'restaurante_lanche',
    'casa_utilidades',
    'saude',
    'transporte',
    'lazer_outros'
}

def normalizar_tipo_pg(tipo: str) -> str:
    t = tipo.lower().strip()
    if 'credito' in t or 'cartao' in t or 'cartão' in t:
        return 'credito'
    elif 'debito' in t or 'débito' in t:
        return 'debito'
    elif t in ('pix', 'dinheiro', 'outros'):
        return t
    return 'outros'

def calcular_mes_vigente(data_compra, tipo_pg, dia_fechamento):
    """
    Calcula o mês vigente baseado na data de compra, tipo de pagamento e dia de fechamento
    """
    if tipo_pg == 'credito':
        # Para crédito, vai para o próximo mês
        if data_compra.day >= dia_fechamento:
            # Compra após fechamento, vai para mês+2
            next_month = data_compra.month + 2
            year = data_compra.year
            if next_month > 12:
                next_month -= 12
                year += 1
            return f"{year}-{next_month:02d}"
        else:
            # Compra antes do fechamento, vai para mês+1
            next_month = data_compra.month + 1
            year = data_compra.year
            if next_month > 12:
                next_month -= 12
                year += 1
            return f"{year}-{next_month:02d}"
    else:
        # Débito, PIX, dinheiro - fica no mês atual
        return f"{data_compra.year}-{data_compra.month:02d}"

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

    # 🔥 ROTAS DE COLABORADORES
    @app.route('/api/colaboradores', methods=['GET', 'POST'])
    @jwt_required()
    def colaboradores():
        if request.method == 'GET':
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                    colaboradores = cursor.fetchall()
                    return jsonify(colaboradores)
            except Exception as e:
                logger.error(f"Erro ao buscar colaboradores: {str(e)}")
                return jsonify({'error': 'Erro interno do servidor'}), 500
        else:
            # POST - Criar colaborador
            try:
                data = request.get_json()
                nome = data.get('nome')
                dia_fechamento = data.get('dia_fechamento')
                
                if not nome or not dia_fechamento:
                    return jsonify({'error': 'Nome e dia_fechamento são obrigatórios'}), 400
                
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                        (nome, dia_fechamento)
                    )
                    new_id = cursor.fetchone()[0]
                    conn.commit()
                    return jsonify({'id': new_id, 'message': 'Colaborador criado com sucesso'}), 201
            except Exception as e:
                logger.error(f"Erro ao criar colaborador: {str(e)}")
                return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/colaboradores/<int:id>', methods=['PUT', 'DELETE'])
    @jwt_required()       
    def colaborador_id(id):
        if request.method == 'PUT':
            data = request.json
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE colaborador SET nome=%s, dia_fechamento=%s WHERE id=%s",
                        (data['nome'], data['dia_fechamento'], id)
                    )
                    conn.commit()
                    return jsonify({"message": "Atualizado"})
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM colaborador WHERE id=%s", (id,))
                    conn.commit()
                    return jsonify({"message": "Deletado"})

    # 🔥 ROTAS DE DESPESAS
    @app.route('/api/despesas', methods=['GET', 'POST'])
    @jwt_required()
    def despesas():
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

    @app.route('/api/divisao/<mes_ano>', methods=['GET'])
    @jwt_required()
    def obter_status_divisao(mes_ano):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT paga, data_acerto FROM divisao_mensal WHERE mes_ano = %s", (mes_ano,))
                row = cur.fetchone()
                if row:
                    return jsonify({
                        "mes_ano": mes_ano,
                        "paga": row['paga'],
                        "data_acerto": row['data_acerto'].isoformat() if row['data_acerto'] else None
                    })
                else:
                    return jsonify({"mes_ano": mes_ano, "paga": False, "data_acerto": None})

    @app.route('/api/divisao/<mes_ano>/marcar-pago', methods=['POST'])
    @jwt_required()
    def marcar_divisao_como_paga(mes_ano):
        data_acerto = request.json.get('data_acerto')
        if data_acerto:
            try:
                date.fromisoformat(data_acerto)
            except ValueError:
                return jsonify({"error": "data_acerto deve estar no formato YYYY-MM-DD"}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO divisao_mensal (mes_ano, paga, data_acerto)
                    VALUES (%s, true, %s)
                    ON CONFLICT (mes_ano)
                    DO UPDATE SET paga = true, data_acerto = EXCLUDED.data_acerto
                """, (mes_ano, data_acerto))
                conn.commit()
                return jsonify({"mes_ano": mes_ano, "paga": True, "data_acerto": data_acerto}), 200

    @app.route('/api/divisao/<mes_ano>/desmarcar-pago', methods=['POST'])
    @jwt_required()
    def desmarcar_divisao_como_paga(mes_ano):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE divisao_mensal SET paga = false, data_acerto = NULL
                    WHERE mes_ano = %s
                """, (mes_ano,))
                conn.commit()
                return jsonify({"mes_ano": mes_ano, "paga": False}), 200

    @app.route('/api/despesas/<int:id>', methods=['PUT', 'DELETE'])
    @jwt_required()
    def despesa_id(id):
        if request.method == 'PUT':
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
                        UPDATE despesa
                        SET data_compra=%s, mes_vigente=%s, descricao=%s, valor=%s, tipo_pg=%s, colaborador_id=%s, categoria=%s
                        WHERE id=%s
                    """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria, id))
                    conn.commit()
                    return jsonify({"message": "Atualizado"})
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM despesa WHERE id=%s", (id,))
                    conn.commit()
                    return jsonify({"message": "Deletado"})

    # 🔥 ROTAS DE RENDAS
    @app.route('/api/rendas', methods=['GET', 'POST'])
    @jwt_required()
    def rendas():
        if request.method == 'GET':
            mes = request.args.get('mes')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if mes:
                        cur.execute("""
                            SELECT rm.*, c.nome FROM renda_mensal rm
                            JOIN colaborador c ON rm.colaborador_id = c.id
                            WHERE rm.mes_ano = %s
                        """, (mes,))
                    else:
                        cur.execute("""
                            SELECT rm.*, c.nome FROM renda_mensal rm
                            JOIN colaborador c ON rm.colaborador_id = c.id
                        """)
                    rendas = [dict(r) for r in cur.fetchall()]
                    return jsonify({"rendas": rendas})
        else:
            data = request.json
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO renda_mensal (colaborador_id, mes_ano, valor)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (colaborador_id, mes_ano)
                        DO UPDATE SET valor = EXCLUDED.valor
                        RETURNING id
                    """, (data['colaborador_id'], data['mes_ano'], data['valor']))
                    conn.commit()
                    return jsonify({"id": cur.fetchone()['id']}), 201

    @app.route('/api/rendas/<int:id>', methods=['PUT', 'DELETE'])
    @jwt_required()
    def renda_id(id):
        if request.method == 'PUT':
            data = request.json
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE renda_mensal SET valor=%s WHERE id=%s",
                        (data['valor'], id)
                    )
                    conn.commit()
                    return jsonify({"message": "Atualizado"})
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM renda_mensal WHERE id=%s", (id,))
                    conn.commit()
                    return jsonify({"message": "Deletado"})

    # 🔥 RESUMO FINANCEIRO
    @app.route('/api/resumo', methods=['GET'])
    @jwt_required()
    def obter_resumo():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Total despesas
                cursor.execute("SELECT COALESCE(SUM(valor), 0) as total_despesas FROM despesa")
                total_despesas = cursor.fetchone()['total_despesas'] or 0
                
                # Total rendas
                cursor.execute("SELECT COALESCE(SUM(valor), 0) as total_rendas FROM renda_mensal")
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

    # 🔥 RESUMO DETALHADO POR MÊS
    @app.route('/api/resumo/<mes_ano>', methods=['GET'])
    @jwt_required()
    def obter_resumo_mes(mes_ano):
        try:
            if not re.match(r'^\d{4}-\d{2}$', mes_ano):
                return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Total de despesas do mês
                cursor.execute("SELECT COALESCE(SUM(valor), 0) AS total FROM despesa WHERE mes_vigente = %s", (mes_ano,))
                total_despesas = float(cursor.fetchone()['total'])

                # Rendas por colaborador
                cursor.execute("""
                    SELECT c.id, c.nome, r.valor
                    FROM colaborador c
                    LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                    ORDER BY c.id
                """, (mes_ano,))
                
                rendas = cursor.fetchall()
                for renda in rendas:
                    if renda.get('valor'):
                        renda['valor'] = float(renda['valor'])

                # Montar resposta
                resumo_data = {
                    "mes": mes_ano,
                    "total_despesas": round(total_despesas, 2),
                    "colaboradores": []
                }

                for renda in rendas:
                    resumo_data["colaboradores"].append({
                        "id": renda['id'],
                        "nome": renda['nome'],
                        "renda": renda['valor'] if renda['valor'] else 0,
                        "percentual": 0.5  # Placeholder - ajustar conforme lógica de divisão
                    })

                return jsonify(resumo_data)

        except Exception as e:
            logger.error(f"Erro no resumo do mês: {str(e)}")
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