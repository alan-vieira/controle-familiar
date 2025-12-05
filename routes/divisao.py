# routes/divisao.py
from flask import Blueprint, request, jsonify
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
from datetime import date
import re
import logging
from app.middleware.auth_middleware import require_supabase_auth

logger = logging.getLogger(__name__)

divisao_bp = Blueprint('divisao', __name__)

def validar_mes_ano(mes_ano):
    return bool(re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano))

@divisao_bp.route('/divisao/<mes_ano>', methods=['GET'])
@require_supabase_auth
def obter_status_divisao(mes_ano):
    if not validar_mes_ano(mes_ano):
        return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT paga, data_acerto FROM divisao_mensal WHERE mes_ano = %s",
                    (mes_ano,)
                )
                row = cur.fetchone()

                if row:
                    return jsonify({
                        "mes_ano": mes_ano,
                        "paga": row['paga'],
                        "data_acerto": row['data_acerto'].isoformat() if row['data_acerto'] else None
                    })
                else:
                    return jsonify({
                        "mes_ano": mes_ano,
                        "paga": False,
                        "data_acerto": None
                    })
    except Exception as e:
        logger.error(f"Erro em obter_status_divisao: {e}")
        return jsonify({"error": "Erro interno ao buscar status da divisão"}), 500

@divisao_bp.route('/divisao/<mes_ano>/marcar-pago', methods=['POST'])
@require_supabase_auth
def marcar_divisao_como_paga(mes_ano):
    if not validar_mes_ano(mes_ano):
        return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

    data = request.get_json() or {}
    data_acerto = data.get('data_acerto')

    if data_acerto:
        try:
            date.fromisoformat(data_acerto)
        except ValueError:
            return jsonify({"error": "data_acerto deve estar no formato YYYY-MM-DD"}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO divisao_mensal (mes_ano, paga, data_acerto)
                    VALUES (%s, true, %s)
                    ON CONFLICT (mes_ano)
                    DO UPDATE SET paga = true, data_acerto = EXCLUDED.data_acerto
                    RETURNING mes_ano, paga, data_acerto
                """, (mes_ano, data_acerto))
                
                result = cur.fetchone()

                return jsonify({
                    "mes_ano": result['mes_ano'],
                    "paga": result['paga'],
                    "data_acerto": result['data_acerto'].isoformat() if result['data_acerto'] else None
                }), 200
    except Exception as e:
        logger.error(f"Erro ao marcar divisão como paga: {e}")
        return jsonify({"error": "Erro interno ao atualizar divisão"}), 500

@divisao_bp.route('/divisao/<mes_ano>/desmarcar-pago', methods=['POST'])
@require_supabase_auth
def desmarcar_divisao_como_paga(mes_ano):
    if not validar_mes_ano(mes_ano):
        return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    UPDATE divisao_mensal 
                    SET paga = false, data_acerto = NULL 
                    WHERE mes_ano = %s
                    RETURNING mes_ano, paga, data_acerto
                """, (mes_ano,))
                

                if cur.rowcount == 0:
                    cur.execute("""
                        INSERT INTO divisao_mensal (mes_ano, paga)
                        VALUES (%s, false)
                        RETURNING mes_ano, paga, data_acerto
                    """, (mes_ano,))
                    

                result = cur.fetchone()
                return jsonify({
                    "mes_ano": result['mes_ano'],
                    "paga": result['paga'],
                    "data_acerto": result['data_acerto']
                }), 200
    except Exception as e:
        logger.error(f"Erro ao desmarcar divisão como paga: {e}")
        return jsonify({"error": "Erro interno ao atualizar divisão"}), 500
