# routes/despesas.py
"""
Despesas routes - Protected with JWT authentication.

All endpoints require valid JWT token.
"""
from decimal import Decimal, InvalidOperation
from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from connection import get_db_connection, get_db_cursor
from psycopg2.extras import RealDictCursor
from utils.date_utils import calcular_mes_vigente
from utils.json_utils import json_response
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
despesas_bp = Blueprint('despesas', __name__)

CATEGORIAS_VALIDAS = {
    'moradia', 'alimentacao', 'restaurante_lanche',
    'casa_utilidades', 'saude', 'transporte', 'lazer_outros'
}

TIPOS_PG_VALIDOS = {'credito', 'debito', 'pix', 'dinheiro', 'outros'}


def _error_response(message: str, code: str, status: int = 400):
    return json_response({'error': message, 'code': code}, status)


def _success_response(data: dict, status: int = 200):
    return json_response(data, status)


def normalizar_tipo_pg(tipo: str) -> str:
    """Normaliza variações de tipo de pagamento para o enum do banco."""
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
    """List expenses, optionally filtered by month."""
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

        # Convert date to string, keep Decimal as-is (json_response handles it)
        for d in despesas:
            if d.get('data_compra'):
                d['data_compra'] = d['data_compra'].strftime('%Y-%m-%d')

        logger.info(f"GET /api/despesas - Encontrados {len(despesas)} registros")
        return _success_response(despesas)

    except Exception as e:
        logger.error(f"ERRO GET /api/despesas: {str(e)}", exc_info=True)
        return _error_response('Erro ao buscar despesas', 'FETCH_FAILED', 500)


@despesas_bp.route('/despesas', methods=['POST'])
@jwt_required()
def criar_despesa():
    """Create a new expense."""
    try:
        data = request.get_json()
        if not data:
            return _error_response('Dados JSON inválidos', 'INVALID_JSON')

        # Validation
        required = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return _error_response(f'Campos obrigatórios faltando: {missing}', 'MISSING_FIELDS')

        try:
            data_compra = datetime.strptime(data['data_compra'].split('T')[0], '%Y-%m-%d').date()
            valor = Decimal(str(data['valor']))
            if valor <= Decimal('0'):
                return _error_response('Valor deve ser positivo', 'INVALID_VALUE')
            colab_id = int(data['colaborador_id'])
        except (ValueError, TypeError, InvalidOperation):
            return _error_response('Dados inválidos (data, valor ou colaborador_id)', 'INVALID_DATA')

        # NOVA VALIDAÇÃO: data_compra não pode ser no futuro
        if data_compra > date.today():
            return _error_response('Data da compra não pode ser no futuro', 'FUTURE_DATE')

        tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
        categoria = data['categoria']

        if tipo_pg not in TIPOS_PG_VALIDOS:
            return _error_response('tipo_pg inválido', 'INVALID_TIPO_PG')
        if categoria not in CATEGORIAS_VALIDAS:
            return _error_response('categoria inválida', 'INVALID_CATEGORY')

        # Get collaborator's closing day
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return _error_response('Colaborador não encontrado', 'COLLABORATOR_NOT_FOUND', 404)

                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])

                # Insert expense
                cur.execute("""
                    INSERT INTO despesa (
                        data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data_compra, mes_vigente, data['descricao'], valor, tipo_pg, colab_id, categoria))
                despesa_id = cur.fetchone()['id']

        logger.info(f"Despesa criada: id={despesa_id}, mes={mes_vigente}")
        return _success_response({
            'id': despesa_id,
            'mes_vigente': mes_vigente,
            'message': 'Despesa criada com sucesso'
        }, 201)

    except Exception as e:
        logger.error(f"ERRO POST /api/despesas: {str(e)}", exc_info=True)
        return _error_response('Erro interno', 'CREATE_FAILED', 500)


@despesas_bp.route('/despesas/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def despesa_por_id(id: int):
    """Update or delete an expense by ID."""
    try:
        with get_db_connection() as conn:
            if request.method == 'PUT':
                data = request.get_json()
                if not data:
                    return _error_response('Dados inválidos', 'INVALID_JSON')

                try:
                    data_compra = datetime.strptime(data['data_compra'].split('T')[0], '%Y-%m-%d').date()
                    valor = Decimal(str(data['valor']))
                    if valor <= Decimal('0'):
                        return _error_response('Valor deve ser positivo', 'INVALID_VALUE')
                    colab_id = int(data['colaborador_id'])
                except (ValueError, TypeError, InvalidOperation):
                    return _error_response('Dados inválidos', 'INVALID_DATA')

                # NOVA VALIDAÇÃO: data_compra não pode ser no futuro
                if data_compra > date.today():
                    return _error_response('Data da compra não pode ser no futuro', 'FUTURE_DATE')

                tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
                categoria = data['categoria']

                if tipo_pg not in TIPOS_PG_VALIDOS or categoria not in CATEGORIAS_VALIDAS:
                    return _error_response('Dados inválidos', 'INVALID_DATA')

                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                    colab = cur.fetchone()
                    if not colab:
                        return _error_response('Colaborador não encontrado', 'COLLABORATOR_NOT_FOUND', 404)

                    mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])

                    cur.execute("""
                        UPDATE despesa
                        SET data_compra=%s, mes_vigente=%s, descricao=%s, valor=%s,
                            tipo_pg=%s, colaborador_id=%s, categoria=%s
                        WHERE id=%s
                    """, (data_compra, mes_vigente, data['descricao'], valor,
                          tipo_pg, colab_id, categoria, id))
                    conn.commit()
                    return _success_response({'message': 'Atualizado com sucesso'})

            else:  # DELETE
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM despesa WHERE id = %s", (id,))
                    conn.commit()
                    return _success_response({'message': 'Deletado com sucesso'})

    except Exception as e:
        logger.error(f"Erro em despesa_por_id: {e}")
        return _error_response('Erro interno', 'OPERATION_FAILED', 500)