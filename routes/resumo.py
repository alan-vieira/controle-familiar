# routes/resumo.py
"""
Resumo Financeiro routes - Protected with JWT authentication.

FIX: Decimal -> float na serialização. O Flask envia Decimal como STRING
("1500.50") e o frontend chama .toFixed(2) nesses campos, o que quebra o
render da aba Resumo.
"""
import re
import logging
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint
from flask_jwt_extended import jwt_required
from psycopg2.extras import RealDictCursor
from connection import get_db_connection

logger = logging.getLogger(__name__)
resumo_bp = Blueprint('resumo', __name__)

CENT = Decimal('0.01')


def _money(value) -> float:
    """Decimal -> float com 2 casas (vira JSON number, não string)."""
    return float(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def _error_response(message: str, code: str, status: int = 400):
    from utils.json_utils import json_response
    # 'msg' incluído: o frontend lê errorData.msg para exibir a mensagem
    return json_response({'error': message, 'code': code, 'msg': message}, status)


def _success_response(data: dict, status: int = 200):
    from utils.json_utils import json_response
    return json_response(data, status)


@resumo_bp.route('/resumo/<mes_ano>')
@jwt_required()
def resumo(mes_ano: str):
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
        return _error_response("Formato de mês inválido. Use YYYY-MM.", 'INVALID_MONTH')

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Verificar colaboradores
                cur.execute("SELECT COUNT(*) as total FROM colaborador")
                if cur.fetchone()['total'] == 0:
                    return _error_response("Nenhum colaborador cadastrado", 'NO_COLLABORATORS')

                # 2. Total de despesas
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
                    LEFT JOIN renda_mensal r
                      ON c.id = r.colaborador_id AND r.mes_ano = %s
                    ORDER BY c.nome
                """, (mes_ano,))
                rendas = cur.fetchall()

                for r in rendas:
                    if r['valor'] is not None:
                        r['valor'] = Decimal(str(r['valor']))

                sem_renda = [r['nome'] for r in rendas if r['valor'] is None]
                if sem_renda:
                    return _error_response(
                        f"Rendas não registradas para: {', '.join(sem_renda)}",
                        'MISSING_INCOMES'
                    )

                total_renda = sum((r['valor'] for r in rendas if r['valor']), Decimal('0'))
                if total_renda == 0:
                    return _error_response("Renda total zero para o mês", 'ZERO_INCOME')

                # 4. Pagamentos por colaborador (query única, sem N+1)
                cur.execute("""
                    SELECT colaborador_id, COALESCE(SUM(valor), 0) AS total
                    FROM despesa
                    WHERE mes_vigente = %s
                    GROUP BY colaborador_id
                """, (mes_ano,))
                pagamentos = {
                    row['colaborador_id']: Decimal(str(row['total']))
                    for row in cur.fetchall()
                }

                # 5. Divisão proporcional (cálculo continua em Decimal)
                colaboradores = []
                partes = []
                for r in rendas:
                    valor_renda = r['valor'] or Decimal('0')
                    perc = valor_renda / total_renda
                    deve_pagar = (total_despesas * perc).quantize(CENT, rounding=ROUND_HALF_UP)
                    partes.append(deve_pagar)

                    pagou = pagamentos.get(r['id'], Decimal('0'))
                    saldo = pagou - deve_pagar

                    colaboradores.append({
                        "id": r['id'],
                        "nome": r['nome'],
                        "renda": valor_renda,
                        "percentual": perc * 100,
                        "deve_pagar": deve_pagar,
                        "pagou": pagou,
                        "saldo": saldo,
                        "status": "positivo" if saldo >= 0 else "negativo",
                    })

                # Ajuste do centavo residual no último colaborador
                diferenca = total_despesas - sum(partes)
                if diferenca != 0 and colaboradores:
                    colaboradores[-1]['deve_pagar'] += diferenca
                    colaboradores[-1]['saldo'] -= diferenca

                colaboradores.sort(key=lambda x: x['saldo'], reverse=True)

                # 6. ★ A CORREÇÃO: Decimal -> float antes do JSON ★
                for c in colaboradores:
                    c['renda'] = _money(c['renda'])
                    c['percentual'] = round(float(c['percentual']), 2)
                    c['deve_pagar'] = _money(c['deve_pagar'])
                    c['pagou'] = _money(c['pagou'])
                    c['saldo'] = _money(c['saldo'])

                return _success_response({
                    "mes": mes_ano,
                    "total_despesas": _money(total_despesas),
                    "total_renda": _money(total_renda),
                    "saldo_total": _money(total_renda - total_despesas),
                    "total_colaboradores": len(colaboradores),
                    "colaboradores": colaboradores,
                })

    except Exception as e:
        logger.error(f"Erro ao gerar resumo para {mes_ano}: {e}")
        return _error_response("Erro interno no cálculo do resumo", 'CALCULATION_FAILED', 500)