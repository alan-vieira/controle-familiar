from flask import Blueprint, request, jsonify
from connection import get_db_connection # Ajuste o caminho de importação

colaboradores_bp = Blueprint('colaboradores', __name__)

@colaboradores_bp.route('/colaboradores', methods=['GET', 'POST'])
def colaboradores():
    if request.method == 'GET':
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                colabs = [dict(r) for r in cur.fetchall()] # Usando dict(r) para converter tuplas em dicionários
                return jsonify({"colaboradores": colabs})
    else: # POST
        data = request.json
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                    (data['nome'], data['dia_fechamento'])
                )
                conn.commit()
                return jsonify({"id": cur.fetchone()[0]}), 201 # Pegando o ID retornado corretamente

@colaboradores_bp.route('/colaboradores/<int:id>', methods=['PUT', 'DELETE'])
def colaborador_id(id):
    if request.method == 'PUT':
        data = request.json
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE colaborador SET nome=%s, dia_fechamento=%s WHERE id=%s",
                    (data['nome'], data['dia_fechamento'], id)
                )
                conn.commit()
                return jsonify({"message": "Atualizado"})
    else: # DELETE
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM colaborador WHERE id=%s", (id,))
                conn.commit()
                return jsonify({"message": "Deletado"})
