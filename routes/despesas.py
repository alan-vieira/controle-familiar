# routes/despesas.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
from utils.date_utils import calcular_mes_vigente
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

despesas_bp = Blueprint('despesas', __name__)

CATEGORIAS_VALIDAS = {
    'moradia', 'alimentacao', 'restaurante_lanche',
    'casa_utilidades', 'saude', 'transporte', 'lazer_outros'
}

TIPOS_PG_VALIDOS = {'credito', 'debito', 'pix', 'dinheiro', 'outros'}

def normalizar_tipo_pg(tipo: str) -> str:
    t = tipo.lower().strip()
    if 'credito' in t or 'cartao' in t or 'cartão' in t:
        return 'credito'
    elif 'debito' in t or 'débito' in t:
        return 'debito'
    elif t in ('pix', 'dinheiro', 'outros'):
        return t
    return 'outros'

@despesas_bp.route('/despesas', methods=['GET'])
@jwt_required()
def listar_despesas():
    try:
        logger.info("GET /api/despesas - Iniciando")
        mes = request.args.get('mes_vigente')

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if mes:
                    cur.execute("""
                        SELECT d.*, c.nome AS colaborador_nome
                        FROM despesa d
                        JOIN colaborador c ON d.colaborador_id = c.id
                        WHERE d.mes_vigente = %s
                        ORDER BY d.data_compra DESC
                    """, (mes,))
                else:
                    cur.execute("""
                        SELECT d.*, c.nome AS colaborador_nome
                        FROM despesa d
                        JOIN colaborador c ON d.colaborador_id = c.id
                        ORDER BY d.data_compra DESC
                        LIMIT 100
                    """)
                despesas = cur.fetchall()

        # Conversão segura para JSON
        for d in despesas:
            if d.get('data_compra'):
                d['data_compra'] = d['data_compra'].strftime('%Y-%m-%d')
            if d.get('valor'):
                d['valor'] = float(d['valor'])

        logger.info(f"GET /api/despesas - Encontrados {len(despesas)} registros")
        return jsonify(despesas)

    except Exception as e:
        logger.error(f"ERRO GET /api/despesas: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar despesas'}), 500

@despesas_bp.route('/despesas', methods=['POST'])
@jwt_required()
def criar_despesa():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados JSON inválidos'}), 400

        # Validação
        required = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Campos obrigatórios faltando: {missing}'}), 400

        try:
            data_compra = datetime.strptime(data['data_compra'].split('T')[0], '%Y-%m-%d').date()
            valor = float(data['valor'])
            colab_id = int(data['colaborador_id'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Dados inválidos'}), 400

        tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
        categoria = data['categoria']

        if tipo_pg not in TIPOS_PG_VALIDOS:
            return jsonify({'error': 'tipo_pg inválido'}), 400
        if categoria not in CATEGORIAS_VALIDAS:
            return jsonify({'error': 'categoria inválida'}), 400

        # Obter dia_fechamento do colaborador
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return jsonify({'error': 'Colaborador não encontrado'}), 400

                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])

                # Inserir despesa
                cur.execute("""
                    INSERT INTO despesa (
                        data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data_compra, mes_vigente, data['descricao'], valor, tipo_pg, colab_id, categoria))
                despesa_id = cur.fetchone()[0]
                conn.commit()

        return jsonify({
            'id': despesa_id,
            'mes_vigente': mes_vigente,
            'message': 'Despesa criada com sucesso'
        }), 201

    except Exception as e:
        logger.error(f"ERRO POST /api/despesas: {str(e)}", exc_info=True)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@despesas_bp.route('/despesas/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def despesa_por_id(id):
    try:
        with get_db_connection() as conn:
            if request.method == 'PUT':
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Dados inválidos'}), 400

                data_compra = datetime.strptime(data['data_compra'].split('T')[0], '%Y-%m-%d').date()
                valor = float(data['valor'])
                colab_id = int(data['colaborador_id'])
                tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
                categoria = data['categoria']

                if tipo_pg not in TIPOS_PG_VALIDOS or categoria not in CATEGORIAS_VALIDAS:
                    return jsonify({'error': 'Dados inválidos'}), 400

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                    colab = cur.fetchone()
                    if not colab:
                        return jsonify({'error': 'Colaborador não encontrado'}), 400

                    mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])

                    cur.execute("""
                        UPDATE despesa
                        SET data_compra=%s, mes_vigente=%s, descricao=%s, valor=%s,
                            tipo_pg=%s, colaborador_id=%s, categoria=%s
                        WHERE id=%s
                    """, (data_compra, mes_vigente, data['descricao'], valor,
                          tipo_pg, colab_id, categoria, id))
                    conn.commit()
                    return jsonify({'message': 'Atualizado'}), 200

            else:  # DELETE
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM despesa WHERE id = %s", (id,))
                    conn.commit()
                    return jsonify({'message': 'Deletado'}), 200

    except Exception as e:
        logger.error(f"Erro em despesa_por_id: {e}")
        return jsonify({'error': 'Erro interno'}), 500