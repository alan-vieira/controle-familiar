from flask import Blueprint, request, jsonify
from flask_login import login_required
from connection import get_db_connection

colaboradores_bp = Blueprint('colaboradores', __name__)

@colaboradores_bp.route('/colaboradores', methods=['GET', 'POST'])
@login_required
def colaboradores():
    try:
        if request.method == 'GET':
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                    colabs = [dict(r) for r in cur.fetchall()]
                    return jsonify({"colaboradores": colabs})
        else:  # POST
            data = request.json
            if not data or 'nome' not in data or 'dia_fechamento' not in data:
                return jsonify({"error": "Nome e dia_fechamento são obrigatórios"}), 400
            
            # Validar dia_fechamento
            dia = data['dia_fechamento']
            if not isinstance(dia, int) or dia < 1 or dia > 31:
                return jsonify({"error": "Dia de fechamento deve ser entre 1 e 31"}), 400
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                        (data['nome'], data['dia_fechamento'])
                    )
                    conn.commit()
                    result = cur.fetchone()
                    return jsonify({"id": result['id']}), 201  # ✅ Corrigido: result['id']
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@colaboradores_bp.route('/colaboradores/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def colaborador_id(id):
    try:
        if request.method == 'PUT':
            data = request.json
            if not data or 'nome' not in data or 'dia_fechamento' not in data:
                return jsonify({"error": "Nome e dia_fechamento são obrigatórios"}), 400
            
            # Validar dia_fechamento
            dia = data['dia_fechamento']
            if not isinstance(dia, int) or dia < 1 or dia > 31:
                return jsonify({"error": "Dia de fechamento deve ser entre 1 e 31"}), 400
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE colaborador SET nome=%s, dia_fechamento=%s WHERE id=%s",
                        (data['nome'], data['dia_fechamento'], id)
                    )
                    conn.commit()
                    # Verificar se algum registro foi atualizado
                    if cur.rowcount == 0:
                        return jsonify({"error": "Colaborador não encontrado"}), 404
                    return jsonify({"message": "Atualizado"})
        
        else:  # DELETE
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM colaborador WHERE id=%s", (id,))
                    conn.commit()
                    # Verificar se algum registro foi deletado
                    if cur.rowcount == 0:
                        return jsonify({"error": "Colaborador não encontrado"}), 404
                    return jsonify({"message": "Deletado"})
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
