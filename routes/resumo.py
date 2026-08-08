# routes/resumo.py
"""
Resumo Financeiro routes - Protected with JWT authentication.

All endpoints require valid JWT token.
"""
from decimal import Decimal, ROUND_HALF_UP
from flask import Blueprint
from flask_jwt_extended import jwt_required
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
import re
import logging

logger = logging.getLogger(__name__)
resumo_bp = Blueprint('resumo', __name__)


def _error_response(message: str, code: str, status: int = 400):
    from utils.json_utils import json_response
    return json_response({'error': message, 'code': code}, status)


def _success_response(data: dict, status: int = 200):
    from utils.json_utils import json_response
    return json_response(data, status)


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

                # 2. Total de despesas como Decimal
                cur.execute("""
                    SELECT COALESCE(SUM(valor), 0) AS total
                    FROM despesa
                    WHERE mes_vigente = %s
                """, (mes_ano,))
                total_despesas = Decimal(str(cur.fetchone()['total']))

                # 3. Rendas por colaborador
                cur.execute("""
                    SELECT c.id, c.nome, r.valor
                    FROM colaborador c
                    LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                    ORDER BY c.nome
                """, (mes_ano,))
                rendas = cur.fetchall()

                # Converter valores para Decimal
                for r in rendas:
                    if r['valor'] is not None:
                        r['valor'] = Decimal(str(r['valor']))

                # Verificar rendas faltantes
                colaboradores_sem_renda = [r['nome'] for r in rendas if r['valor'] is None]
                if colaboradores_sem_renda:
                    return _error_response(
                        f"Rendas não registradas para: {', '.join(colaboradores_sem_renda)}",
                        'MISSING_INCOMES',
                        400
                    )

                total_renda = sum(r['valor'] for r in rendas if r['valor'])
                if total_renda == 0:
                    return _error_response("Renda total zero para o mês", 'ZERO_INCOME')

                # 4. OTIMIZAÇÃO: Uma query para todos os pagamentos (elimina N+1)
                cur.execute("""
                    SELECT colaborador_id, COALESCE(SUM(valor), 0) AS total
                    FROM despesa
                    WHERE mes_vigente = %s
                    GROUP BY colaborador_id
                """, (mes_ano,))
                pagamentos_dict = {
                    row['colaborador_id']: Decimal(str(row['total']))
                    for row in cur.fetchall()
                }

                # 5. Montar resposta com cálculo de divisão preciso
                colaboradores = []
                partes = []

                for r in rendas:
                    valor_renda = r['valor'] or Decimal('0')
                    perc = valor_renda / total_renda
                    deve_pagar = (total_despesas * perc).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP
                    )
                    partes.append(deve_pagar)

                    pagou = pagamentos_dict.get(r['id'], Decimal('0'))
                    saldo = pagou - deve_pagar

                    colaboradores.append({
                        "id": r['id'],
                        "nome": r['nome'],
                        "renda": valor_renda.quantize(Decimal('0.01')),
                        "percentual": (perc * 100).quantize(Decimal('0.01')),
                        "deve_pagar": deve_pagar,
                        "pagou": pagou.quantize(Decimal('0.01')),
                        "saldo": saldo.quantize(Decimal('0.01')),
                        "status": "positivo" if saldo >= 0 else "negativo"
                    })

                # Ajustar centavo residual no último colaborador
                soma_partes = sum(partes)
                diferenca = total_despesas - soma_partes
                if diferenca != Decimal('0') and colaboradores:
                    colaboradores[-1]['deve_pagar'] += diferenca
                    colaboradores[-1]['saldo'] -= diferenca

                colaboradores.sort(key=lambda x: x['saldo'], reverse=True)

                return _success_response({
                    "mes": mes_ano,
                    "total_despesas": total_despesas.quantize(Decimal('0.01')),
                    "total_renda": total_renda.quantize(Decimal('0.01')),
                    "saldo_total": (total_renda - total_despesas).quantize(Decimal('0.01')),
                    "total_colaboradores": len(colaboradores),
                    "colaboradores": colaboradores
                })

    except Exception as e:
        logger.error(f"Erro ao gerar resumo para {mes_ano}: {e}")
        return _error_response("Erro interno no cálculo do resumo", 'CALCULATION_FAILED', 500)