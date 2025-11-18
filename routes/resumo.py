import re
from flask import Blueprint, jsonify
from connection import get_db_connection # Ajuste o caminho de importação

resumo_bp = Blueprint('resumo', __name__)

@resumo_bp.route('/resumo/<mes_ano>')
def resumo(mes_ano):
    try:
        if not re.match(r'^\d{4}-\d{2}$', mes_ano):
            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total de despesas
                cur.execute("SELECT COALESCE(SUM(valor), 0) AS total FROM despesa WHERE mes_vigente = %s", (mes_ano,))
                total_despesas = float(cur.fetchone()['total'])

                # Rendas por colaborador
                cur.execute("""
                    SELECT c.id, c.nome, r.valor
                    FROM colaborador c
                    LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                    ORDER BY c.id
                """, (mes_ano,))
                rendas = []
                for row in cur.fetchall():
                    valor = float(row['valor']) if row['valor'] is not None else None
                    rendas.append({
                        'id': row['id'],
                        'nome': row['nome'],
                        'valor': valor
                    })

                # Verificar se todas as rendas estão preenchidas
                for r in rendas:
                    if r['valor'] is None:
                        return jsonify({"error": f"Renda não registrada para {r['nome']} em {mes_ano}"}), 400

                total_renda = sum(r['valor'] for r in rendas)
                if total_renda == 0:
                    return jsonify({"error": "Renda total zero"}), 400

                # Quanto cada um pagou em despesas
                pagamentos = {}
                for r in rendas:
                    cur.execute("""
                        SELECT COALESCE(SUM(valor), 0) AS total
                        FROM despesa
                        WHERE colaborador_id = %s AND mes_vigente = %s
                    """, (r['id'], mes_ano))
                    pagamentos[r['id']] = float(cur.fetchone()['total'])

                # Montar resposta
                resumo_data = {
                    "mes": mes_ano,
                    "total_despesas": round(total_despesas, 2),
                    "total_renda": round(total_renda, 2),
                    "colaboradores": []
                }

                for r in rendas:
                    perc = r['valor'] / total_renda
                    deve_pagar = total_despesas * perc
                    pagou = pagamentos[r['id']]
                    saldo = pagou - deve_pagar

                    resumo_data["colaboradores"].append({
                        "id": r['id'],
                        "nome": r['nome'],
                        "renda": round(r['valor'], 2),
                        "percentual": round(perc, 4),
                        "deve_pagar": round(deve_pagar, 2),
                        "pagou": round(pagou, 2),
                        "saldo": round(saldo, 2)
                    })

                return jsonify(resumo_data)

    except Exception as e:
        print("❌ Erro no resumo:", str(e))
        return jsonify({"error": "Erro interno"}), 500
