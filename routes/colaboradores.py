# routes/colaboradores.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required  # ← JWT, não Flask-Login
from connection import get_db_connection      # ← seu arquivo de conexão
from psycopg2.extras import RealDictCursor    # ← para dicionários no PostgreSQL
import logging

logger = logging.getLogger(__name__)

colaboradores_bp = Blueprint('colaboradores', __name__)

@colaboradores_bp.route('/colaboradores', methods=['GET'])
@jwt_required()  # ← Correto para JWT
def listar_colaboradores():
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:  # ← Correto
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                colaboradores = cur.fetchall()
        logger.info(f"GET /api/colaboradores - Encontrados {len(colaboradores)} registros")
        return jsonify(colaboradores)
    except Exception as e:
        logger.error(f"ERRO GET /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar colaboradores'}), 500

@colaboradores_bp.route('/colaboradores', methods=['POST'])
@jwt_required()
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
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                    (nome, dia)
                )
                colaborador_id = cur.fetchone()[0]
                conn.commit()

        return jsonify({
            'id': colaborador_id,
            'nome': nome,
            'dia_fechamento': dia,
            'message': 'Colaborador criado com sucesso'
        }), 201

    except Exception as e:
        logger.error(f"ERRO POST /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
