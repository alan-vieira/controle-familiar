# routes/resumo.py
from flask import Blueprint, jsonify
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
import re
import logging
from app.middleware.auth_middleware import require_supabase_auth

logger = logging.getLogger(__name__)

resumo_bp = Blueprint('resumo', __name__)

@resumo_bp.route('/resumo/<mes_ano>')
@require_supabase_auth
def resumo(mes_ano):
    # Validar formato do mês
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
        return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Verificar colaboradores
                cur.execute("SELECT COUNT(*) as total FROM colaborador")
                total_colabs = cur.fetchone()['total']
                if total_colabs == 0:
                    return jsonify({"error": "Nenhum colaborador cadastrado"}), 400

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
                    return jsonify({
                        "error": f"Rendas não registradas para: {', '.join(colaboradores_sem_renda)}",
                        "colaboradores_sem_renda": colaboradores_sem_renda
                    }), 400

                total_renda = sum(float(r['valor']) for r in rendas)
                if total_renda == 0:
                    return jsonify({"error": "Renda total zero para o mês"}), 400

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

                return jsonify({
                    "mes": mes_ano,
                    "total_despesas": round(total_despesas, 2),
                    "total_renda": round(total_renda, 2),
                    "saldo_total": round(total_renda - total_despesas, 2),
                    "total_colaboradores": len(colaboradores),
                    "colaboradores": colaboradores
                })

    except Exception as e:
        logger.error(f"Erro ao gerar resumo para {mes_ano}: {e}")
        return jsonify({"error": "Erro interno no cálculo do resumo"}), 500
