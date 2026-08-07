# routes/rendas.py
"""
Rendas routes - Protected with JWT authentication.

All endpoints require valid JWT token.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from connection import get_db_connection, get_db_cursor
from psycopg2.extras import RealDictCursor
import re
import logging

logger = logging.getLogger(__name__)
rendas_bp = Blueprint('rendas', __name__)


def _error_response(message: str, code: str, status: int = 400) -> tuple:
    return jsonify({'error': message, 'code': code}), status


def _success_response(data: dict, status: int = 200) -> tuple:
    return jsonify(data), status


def validar_mes_ano(mes_ano: str) -> bool:
    return bool(re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano))


def validar_renda_data(data: dict) -> list:
    errors = []
    if not isinstance(data, dict):
        return ["Corpo da requisição deve ser um JSON válido"]
    if not isinstance(data.get('colaborador_id'), int):
        errors.append("colaborador_id é obrigatório e deve ser um número inteiro")
    if not validar_mes_ano(data.get('mes_ano', '')):
        errors.append("mes_ano é obrigatório e deve estar no formato YYYY-MM")
    if not isinstance(data.get('valor'), (int, float)) or (data.get('valor') or -1) < 0:
        errors.append("valor é obrigatório e deve ser um número positivo")
    return errors


@rendas_bp.route('/rendas', methods=['GET', 'POST'])
@jwt_required()
def rendas():
    try:
        if request.method == 'GET':
            mes = request.args.get('mes')
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if mes:
                        if not validar_mes_ano(mes):
                            return _error_response("Formato de mês inválido. Use YYYY-MM.", 'INVALID_MONTH')
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
                    return _success_response(cur.fetchall())

        else:  # POST
            data = request.get_json()
            errors = validar_renda_data(data)
            if errors:
                return _error_response(errors[0], 'VALIDATION_FAILED', 400)

            with get_db_cursor() as cur:
                cur.execute("SELECT id FROM colaborador WHERE id = %s", (data['colaborador_id'],))
                if not cur.fetchone():
                    return _error_response("Colaborador não encontrado", 'COLLABORATOR_NOT_FOUND', 404)

                cur.execute("""
                    INSERT INTO renda_mensal (colaborador_id, mes_ano, valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (colaborador_id, mes_ano)
                    DO UPDATE SET valor = EXCLUDED.valor
                    RETURNING id
                """, (data['colaborador_id'], data['mes_ano'], data['valor']))
                result = cur.fetchone()
                return _success_response({
                    "id": result['id'],
                    "message": "Renda registrada/atualizada com sucesso"
                }, 201)

    except Exception as e:
        logger.error(f"Erro em /rendas: {e}")
        return _error_response("Erro interno no processamento de rendas", 'OPERATION_FAILED', 500)


@rendas_bp.route('/rendas/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def renda_id(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM renda_mensal WHERE id = %s", (id,))
                if not cur.fetchone():
                    return _error_response("Renda não encontrada", 'NOT_FOUND', 404)

                if request.method == 'PUT':
                    data = request.get_json()
                    if not isinstance(data, dict) or not isinstance(data.get('valor'), (int, float)) or data.get('valor', -1) < 0:
                        return _error_response("Valor deve ser um número positivo", 'INVALID_VALUE')

                    cur.execute("UPDATE renda_mensal SET valor = %s WHERE id = %s", (data['valor'], id))
                    conn.commit()
                    return _success_response({"message": "Renda atualizada com sucesso"})

                else:  # DELETE
                    cur.execute("DELETE FROM renda_mensal WHERE id = %s", (id,))
                    conn.commit()
                    return _success_response({"message": "Renda deletada com sucesso"})

    except Exception as e:
        logger.error(f"Erro em /rendas/{id}: {e}")
        return _error_response("Erro interno", 'OPERATION_FAILED', 500)