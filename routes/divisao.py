from flask import Blueprint, request, jsonify
from connection import get_db_connection # Ajuste o caminho de importação
from datetime import date

divisao_bp = Blueprint('divisao', __name__)

@divisao_bp.route('/divisao/<mes_ano>', methods=['GET'])
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

@divisao_bp.route('/divisao/<mes_ano>/marcar-pago', methods=['POST'])
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

@divisao_bp.route('/divisao/<mes_ano>/desmarcar-pago', methods=['POST'])
def desmarcar_divisao_como_paga(mes_ano):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE divisao_mensal SET paga = false, data_acerto = NULL
                WHERE mes_ano = %s
            """, (mes_ano,))
            conn.commit()
            return jsonify({"mes_ano": mes_ano, "paga": False}), 200
