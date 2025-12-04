# routes/rendas.py
from flask import Blueprint, request, jsonify
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
import re
import logging
from app.middleware.auth import require_supabase_auth

logger = logging.getLogger(__name__)

rendas_bp = Blueprint('rendas', __name__)

def validar_mes_ano(mes_ano):
    return bool(re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano))

def validar_renda_data(data):
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
@require_supabase_auth
def rendas():
    try:
        if request.method == 'GET':
            mes = request.args.get('mes')
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if mes:
                        if not validar_mes_ano(mes):
                            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400
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
                    return jsonify(cur.fetchall())

        else:  # POST
            data = request.get_json()
            errors = validar_renda_data(data)
            if errors:
                return jsonify({"errors": errors}), 400

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT id FROM colaborador WHERE id = %s", (data['colaborador_id'],))
                    if not cur.fetchone():
                        return jsonify({"error": "Colaborador não encontrado"}), 400

                    cur.execute("""
                        INSERT INTO renda_mensal (colaborador_id, mes_ano, valor)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (colaborador_id, mes_ano)
                        DO UPDATE SET valor = EXCLUDED.valor
                        RETURNING id
                    """, (data['colaborador_id'], data['mes_ano'], data['valor']))
                    conn.commit()
                    result = cur.fetchone()
                    return jsonify({
                        "id": result['id'],
                        "message": "Renda registrada/atualizada com sucesso"
                    }), 201

    except Exception as e:
        logger.error(f"Erro em /rendas: {e}")
        return jsonify({"error": "Erro interno no processamento de rendas"}), 500

@rendas_bp.route('/rendas/<int:id>', methods=['PUT', 'DELETE'])
@require_supabase_auth
def renda_id(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM renda_mensal WHERE id = %s", (id,))
                if not cur.fetchone():
                    return jsonify({"error": "Renda não encontrada"}), 404

                if request.method == 'PUT':
                    data = request.get_json()
                    if not isinstance(data, dict) or not isinstance(data.get('valor'), (int, float)) or data.get('valor', -1) < 0:
                        return jsonify({"error": "Valor deve ser um número positivo"}), 400

                    cur.execute("UPDATE renda_mensal SET valor = %s WHERE id = %s", (data['valor'], id))
                    conn.commit()
                    return jsonify({"message": "Renda atualizada com sucesso"})

                else:  # DELETE
                    cur.execute("DELETE FROM renda_mensal WHERE id = %s", (id,))
                    conn.commit()
                    return jsonify({"message": "Renda deletada com sucesso"})

    except Exception as e:
        logger.error(f"Erro em /rendas/{id}: {e}")
        return jsonify({"error": "Erro interno"}), 500
