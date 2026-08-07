# routes/resumo.py
"""
Resumo Financeiro routes - Protected with JWT authentication.

All endpoints require valid JWT token.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from connection import get_db_connection, get_db_cursor
from psycopg2.extras import RealDictCursor
import re
import logging

logger = logging.getLogger(__name__)
resumo_bp = Blueprint('resumo', __name__)


def _error_response(message: str, code: str, status: int = 400) -> tuple:
    return jsonify({'error': message, 'code': code}), status


def _success_response(data: dict, status: int = 200) -> tuple:
    return jsonify(data), status


@resumo_bp.route('/resumo/<mes_ano>')
@jwt_required()
def resumo(mes_ano: str):
    # Validar formato do mês
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
        return _error_response("Formato de mês inválido. Use YYYY-MM.", 'INVALID_MONTH')

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Verificar colaboradores
                cur.execute("SELECT COUNT(*) as total FROM colaborador")
                total_colabs = cur.fetchone()['total']
                if total_colabs == 0:
                    return _error_response("Nenhum colaborador cadastrado", 'NO_COLLABORATORS')

                # 2. Total de despesas
                cur.execute("""
                    SELECT COALESCE(SUM(valor), 0) AS total
                    FROM despesa
                    WHERE mes_vigente = %s
                """, (mes_ano,))
                total_despesas = float(cur.fetchone()['total'])

                # 3. Rendas por colaborador
                cur.execute("""
                    SELECT c.id, c.nome, r.valor
                    FROM colaborador c
                    LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                    ORDER BY c.nome
                """, (mes_ano,))
                rendas = cur.fetchall()

                # Verificar rendas faltantes
                colaboradores_sem_renda = [r['nome'] for r in rendas if r['valor'] is None]
                if colaboradores_sem_renda:
                    return _error_response(
                        f"Rendas não registradas para: {', '.join(colaboradores_sem_renda)}",
                        'MISSING_INCOMES',
                        400
                    )

                total_renda = sum(float(r['valor']) for r in rendas)
                if total_renda == 0:
                    return _error_response("Renda total zero para o mês", 'ZERO_INCOME')

                # 4. Pagamentos por colaborador
                pagamentos = {}
                for r in rendas:
                    cur.execute("""
                        SELECT COALESCE(SUM(valor), 0) AS total
                        FROM despesa
                        WHERE colaborador_id = %s AND mes_vigente = %s
                    """, (r['id'], mes_ano))
                    pagamentos[r['id']] = float(cur.fetchone()['total'])

                # 5. Montar resposta
                colaboradores = []
                for r in rendas:
                    valor_renda = float(r['valor'])
                    perc = valor_renda / total_renda
                    deve_pagar = total_despesas * perc
                    pagou = pagamentos[r['id']]
                    saldo = pagou - deve_pagar

                    colaboradores.append({
                        "id": r['id'],
                        "nome": r['nome'],
                        "renda": round(valor_renda, 2),
                        "percentual": round(perc * 100, 2),
                        "deve_pagar": round(deve_pagar, 2),
                        "pagou": round(pagou, 2),
                        "saldo": round(saldo, 2),
                        "status": "positivo" if saldo >= 0 else "negativo"
                    })

                colaboradores.sort(key=lambda x: x['saldo'], reverse=True)

                return _success_response({
                    "mes": mes_ano,
                    "total_despesas": round(total_despesas, 2),
                    "total_renda": round(total_renda, 2),
                    "saldo_total": round(total_renda - total_despesas, 2),
                    "total_colaboradores": len(colaboradores),
                    "colaboradores": colaboradores
                })

    except Exception as e:
        logger.error(f"Erro ao gerar resumo para {mes_ano}: {e}")
        return _error_response("Erro interno no cálculo do resumo", 'CALCULATION_FAILED', 500)