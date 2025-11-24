from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.connection import get_db_connection
import logging
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

colaboradores_bp = Blueprint('colaboradores', __name__)

@colaboradores_bp.route('/api/colaboradores', methods=['GET'])
@jwt_required()
def listar_colaboradores():
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)  # Retorna dicionários
            cursor.execute("SELECT * FROM colaborador ORDER BY nome")
            colaboradores = cursor.fetchall()
        
        logger.info(f"GET /api/colaboradores - Encontrados {len(colaboradores)} registros")
        return jsonify(colaboradores)
        
    except Exception as e:
        logger.error(f"ERRO GET /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar colaboradores'}), 500

@colaboradores_bp.route('/api/colaboradores', methods=['POST'])
@jwt_required()
def criar_colaborador():
    try:
        data = request.get_json()
        logger.info(f"POST /api/colaboradores - Dados: {data}")
        
        if not data:
            return jsonify({'error': 'Dados JSON inválidos'}), 400
        
        required = ['nome', 'dia_fechamento']
        missing = [field for field in required if field not in data or data[field] in [None, '']]
        
        if missing:
            return jsonify({'error': f'Campos obrigatórios faltando: {missing}'}), 400
        
        # Validar dia_fechamento
        try:
            dia = int(data['dia_fechamento'])
            if dia < 1 or dia > 31:
                return jsonify({'error': 'dia_fechamento deve estar entre 1 e 31'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'dia_fechamento deve ser um número'}), 400
        
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
            'id': colaborador_id,
            'nome': data['nome'],
            'dia_fechamento': dia,
            'message': 'Colaborador criado com sucesso'
        }
        
        logger.info(f"POST /api/colaboradores - Sucesso: {response_data}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"ERRO POST /api/colaboradores: {str(e)}", exc_info=True)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500