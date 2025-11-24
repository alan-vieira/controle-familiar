# blueprints/colaboradores.py
from flask import Blueprint, request, jsonify
<<<<<<< HEAD:routes/colaboradores.py
from flask_jwt_extended import jwt_required  # ← JWT, não Flask-Login
from connection import get_db_connection      # ← seu arquivo de conexão
from psycopg2.extras import RealDictCursor    # ← para dicionários no PostgreSQL
=======
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.connection import get_db_connection
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/api/routes/colaboradores.py
import logging
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

colaboradores_bp = Blueprint('colaboradores', __name__)

<<<<<<< HEAD:routes/colaboradores.py
@colaboradores_bp.route('/colaboradores', methods=['GET'])
@jwt_required()  # ← Correto para JWT
def listar_colaboradores():
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:  # ← Correto
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                colaboradores = cur.fetchall()
=======
@colaboradores_bp.route('/api/colaboradores', methods=['GET'])
@jwt_required()
def listar_colaboradores():
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)  # Retorna dicionários
            cursor.execute("SELECT * FROM colaborador ORDER BY nome")
            colaboradores = cursor.fetchall()
        
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/api/routes/colaboradores.py
        logger.info(f"GET /api/colaboradores - Encontrados {len(colaboradores)} registros")
        return jsonify(colaboradores)
    except Exception as e:
        logger.error(f"ERRO GET /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar colaboradores'}), 500

<<<<<<< HEAD:routes/colaboradores.py
@colaboradores_bp.route('/colaboradores', methods=['POST'])
=======
@colaboradores_bp.route('/api/colaboradores', methods=['POST'])
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/api/routes/colaboradores.py
@jwt_required()
def criar_colaborador():
    try:
        data = request.get_json()
        if not 
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
<<<<<<< HEAD:routes/colaboradores.py

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                    (nome, dia)
                )
                colaborador_id = cur.fetchone()[0]
                conn.commit()

        return jsonify({
=======
        
        # Inserir no banco
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s)",
                (data['nome'], dia)
            )
            
            conn.commit()
            colaborador_id = cursor.lastrowid
        
        response_data = {
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/api/routes/colaboradores.py
            'id': colaborador_id,
            'nome': nome,
            'dia_fechamento': dia,
            'message': 'Colaborador criado com sucesso'
        }), 201

    except Exception as e:
        logger.error(f"ERRO POST /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500