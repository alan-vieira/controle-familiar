import re
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from src.models.connection import get_db_connection
from psycopg2.extras import RealDictCursor

resumo_bp = Blueprint('resumo', __name__)

@resumo_bp.route('/resumo/<mes_ano>')
@jwt_required()
def resumo(mes_ano):
    try:
        # Validar formato do mês
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            # 1. Verificar se existem colaboradores
            cursor.execute("SELECT COUNT(*) as total FROM colaborador")
            total_colabs = cursor.fetchone()['total']
            
            if total_colabs == 0:
                return jsonify({"error": "Nenhum colaborador cadastrado"}), 400

            # 2. Total de despesas do mês
            cursor.execute("""
                SELECT COALESCE(SUM(valor), 0) AS total 
                FROM despesa 
                WHERE mes_vigente = %s
            """, (mes_ano,))
            total_despesas = float(cursor.fetchone()['total'])

            # 3. Rendas por colaborador
            cursor.execute("""
                SELECT c.id, c.nome, r.valor
                FROM colaborador c
                LEFT JOIN renda_mensal r ON c.id = r.colaborador_id AND r.mes_ano = %s
                ORDER BY c.nome
            """, (mes_ano,))
            
            rendas = []
            colaboradores_sem_renda = []
            
            for row in cursor.fetchall():
                valor = float(row['valor']) if row['valor'] is not None else None
                colaborador = {
                    'id': row['id'],
                    'nome': row['nome'],
                    'valor': valor
                }
                rendas.append(colaborador)
                
                if valor is None:
                    colaboradores_sem_renda.append(row['nome'])

            # 4. Verificar se todas as rendas estão preenchidas
            if colaboradores_sem_renda:
                return jsonify({
                    "error": f"Rendas não registradas para: {', '.join(colaboradores_sem_renda)}",
                    "colaboradores_sem_renda": colaboradores_sem_renda
                }), 400

            total_renda = sum(r['valor'] for r in rendas)
            
            # 5. Verificar se há renda total
            if total_renda == 0:
                return jsonify({
                    "error": "Renda total zero para o mês",
                    "mes": mes_ano,
                    "total_colaboradores": len(rendas)
                }), 400

            # 6. Calcular quanto cada um pagou em despesas
            pagamentos = {}
            for r in rendas:
                cursor.execute("""
                    SELECT COALESCE(SUM(valor), 0) AS total
                    FROM despesa
                    WHERE colaborador_id = %s AND mes_vigente = %s
                """, (r['id'], mes_ano))
                pagamentos[r['id']] = float(cursor.fetchone()['total'])

            # 7. Montar resposta detalhada
            resumo_data = {
                "mes": mes_ano,
                "total_despesas": round(total_despesas, 2),
                "total_renda": round(total_renda, 2),
                "saldo_total": round(total_renda - total_despesas, 2),
                "total_colaboradores": len(rendas),
                "colaboradores": []
            }

            # 8. Calcular valores por colaborador
            for r in rendas:
                perc = r['valor'] / total_renda
                deve_pagar = total_despesas * perc
                pagou = pagamentos[r['id']]
                saldo = pagou - deve_pagar

                resumo_data["colaboradores"].append({
                    "id": r['id'],
                    "nome": r['nome'],
                    "renda": round(r['valor'], 2),
                    "percentual": round(perc * 100, 2),  # Em porcentagem
                    "deve_pagar": round(deve_pagar, 2),
                    "pagou": round(pagou, 2),
                    "saldo": round(saldo, 2),
                    "status": "positivo" if saldo >= 0 else "negativo"
                })

            # 9. Ordenar colaboradores por saldo (maior para menor)
            resumo_data["colaboradores"].sort(key=lambda x: x['saldo'], reverse=True)

            return jsonify(resumo_data)

    except Exception as e:
        print(f"❌ Erro no resumo para {mes_ano}: {str(e)}")
        return jsonify({"error": "Erro interno no cálculo do resumo"}), 500
