from flask import Blueprint, request, jsonify
from connection import get_db_connection # Ajuste o caminho de importação

rendas_bp = Blueprint('rendas', __name__)

@rendas_bp.route('/rendas', methods=['GET', 'POST'])
def rendas():
    if request.method == 'GET':
        mes = request.args.get('mes')
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if mes:
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
                rendas = [dict(r) for r in cur.fetchall()]
                return jsonify({"rendas": rendas})
    else: # POST
        data = request.json
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO renda_mensal (colaborador_id, mes_ano, valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (colaborador_id, mes_ano)
                    DO UPDATE SET valor = EXCLUDED.valor
                    RETURNING id
                """, (data['colaborador_id'], data['mes_ano'], data['valor']))
                conn.commit()
                # Ajuste aqui: pegar o ID retornado da forma correta
                # Se seu psycopg2 retornar um RealDictRow, result['id'] funciona
                # Se retornar uma tupla (id,), use result[0]
                result = cur.fetchone()
                return jsonify({"id": result['id']}) # Assumindo RealDictRow

@rendas_bp.route('/rendas/<int:id>', methods=['PUT', 'DELETE'])
def renda_id(id):
    if request.method == 'PUT':
        data = request.json
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE renda_mensal SET valor=%s WHERE id=%s",
                    (data['valor'], id)
                )
                conn.commit()
                return jsonify({"message": "Atualizado"})
    else: # DELETE
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM renda_mensal WHERE id=%s", (id,))
                conn.commit()
                return jsonify({"message": "Deletado"})
