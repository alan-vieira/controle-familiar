# routes/colaboradores.py
from flask import Blueprint, request, jsonify
from connection import get_db_connection
from psycopg2.extras import RealDictCursor
import logging

# Importe o middleware correto (substituindo jwt_required)
from app.middleware.auth import require_supabase_auth  # ← vamos criar isso

logger = logging.getLogger(__name__)

colaboradores_bp = Blueprint('colaboradores', __name__)

@colaboradores_bp.route('/colaboradores', methods=['GET'])
@require_supabase_auth  # ← substitui @jwt_required()
def listar_colaboradores():
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                colaboradores = cur.fetchall()
        logger.info(f"GET /api/colaboradores - Encontrados {len(colaboradores)} registros")
        return jsonify(colaboradores)
    except Exception as e:
        logger.error(f"ERRO GET /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar colaboradores'}), 500

@colaboradores_bp.route('/colaboradores', methods=['POST'])
@require_supabase_auth
def criar_colaborador():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados JSON inválidos'}), 400

        nome = data.get('nome')
        dia_fechamento = data.get('dia_fechamento')

        if not nome or dia_fechamento is None:
            return jsonify({'error': 'nome e dia_fechamento são obrigatórios'}), 400

        try:
            dia = int(dia_fechamento)
            if not (1 <= dia <= 31):
                return jsonify({'error': 'dia_fechamento deve estar entre 1 e 31'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'dia_fechamento deve ser um número'}), 400

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:  # ← necessário para usar ['id']
                cur.execute(
                    "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                    (nome, dia)
                )
                colaborador_id = cur.fetchone()['id']
                conn.commit()

        return jsonify({
            'id': colaborador_id,
            'nome': nome,
            'dia_fechamento': dia,
            'message': 'Colaborador criado com sucesso'
        }), 201

    except Exception as e:
        logger.error(f"ERRO POST /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro interno no servidor'}), 500

@colaboradores_bp.route('/colaboradores/<int:id>', methods=['PUT', 'DELETE'])
@require_supabase_auth
def colaborador_por_id(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador WHERE id = %s", (id,))
                colaborador = cur.fetchone()
                if not colaborador:
                    return jsonify({"error": "Colaborador não encontrado"}), 404

                if request.method == 'PUT':
                    data = request.get_json()
                    if not data:
                        return jsonify({'error': 'Dados JSON inválidos'}), 400

                    nome = data.get('nome')
                    dia_fechamento = data.get('dia_fechamento')

                    if not nome or dia_fechamento is None:
                        return jsonify({'error': 'nome e dia_fechamento são obrigatórios'}), 400

                    try:
                        dia = int(dia_fechamento)
                        if not (1 <= dia <= 31):
                            return jsonify({'error': 'dia_fechamento deve estar entre 1 e 31'}), 400
                    except (ValueError, TypeError):
                        return jsonify({'error': 'dia_fechamento deve ser um número'}), 400

                    cur.execute(
                        "UPDATE colaborador SET nome = %s, dia_fechamento = %s WHERE id = %s",
                        (nome, dia, id)
                    )
                    conn.commit()
                    return jsonify({"message": "Colaborador atualizado com sucesso"}), 200

                else:  # DELETE
                    cur.execute("DELETE FROM colaborador WHERE id = %s", (id,))
                    conn.commit()
                    return jsonify({"message": "Colaborador excluído com sucesso"}), 200

    except Exception as e:
        logger.error(f"Erro em colaborador_por_id (id={id}): {str(e)}", exc_info=True)
        return jsonify({"error": "Erro interno no servidor"}), 500
