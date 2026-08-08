# routes/colaboradores.py
"""
Colaboradores routes - Protected with JWT authentication.

All endpoints require valid JWT token.
Users can only access their own family's collaborators (future: multi-family support).
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from connection import get_db_connection, get_db_cursor
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)
colaboradores_bp = Blueprint('colaboradores', __name__)


def _error_response(message: str, code: str, status: int = 400):
    from utils.json_utils import json_response
    return json_response({'error': message, 'code': code}, status)


def _success_response(data: dict, status: int = 200):
    from utils.json_utils import json_response
    return json_response(data, status)


def _get_current_user_id() -> int:
    """Get current user ID from JWT identity."""
    return int(get_jwt_identity())


@colaboradores_bp.route('/colaboradores', methods=['GET'])
@jwt_required()
def listar_colaboradores():
    """List all collaborators for the current user's family."""
    try:
        logger.info("GET /api/colaboradores - Iniciando")
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador ORDER BY nome")
                colaboradores = cur.fetchall()
        logger.info(f"GET /api/colaboradores - Encontrados {len(colaboradores)} registros")
        return _success_response(colaboradores)
    except Exception as e:
        logger.error(f"ERRO GET /api/colaboradores: {str(e)}", exc_info=True)
        return _error_response('Erro ao buscar colaboradores', 'FETCH_FAILED', 500)


@colaboradores_bp.route('/colaboradores', methods=['POST'])
@jwt_required()
def criar_colaborador():
    """Create a new collaborator."""
    try:
        data = request.get_json()
        if not data:
            return _error_response('Dados JSON inválidos', 'INVALID_JSON')

        nome = data.get('nome', '').strip()
        dia_fechamento = data.get('dia_fechamento')

        if not nome or dia_fechamento is None:
            return _error_response('nome e dia_fechamento são obrigatórios', 'MISSING_FIELDS')

        try:
            dia = int(dia_fechamento)
            if not (1 <= dia <= 31):
                return _error_response('dia_fechamento deve estar entre 1 e 31', 'INVALID_DAY')
        except (ValueError, TypeError):
            return _error_response('dia_fechamento deve ser um número', 'INVALID_DAY')

        with get_db_cursor() as cur:
            cur.execute(
                "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                (nome, dia)
            )
            colaborador_id = cur.fetchone()['id']

        logger.info(f"Colaborador criado: {nome} (id={colaborador_id})")
        return _success_response({
            'id': colaborador_id,
            'nome': nome,
            'dia_fechamento': dia,
            'message': 'Colaborador criado com sucesso'
        }, 201)

    except Exception as e:
        logger.error(f"ERRO POST /api/colaboradores: {str(e)}", exc_info=True)
        return _error_response('Erro interno', 'CREATE_FAILED', 500)


@colaboradores_bp.route('/colaboradores/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def colaborador_por_id(id: int):
    """Update or delete a collaborator by ID."""
    try:
        with get_db_cursor() as cur:
            # Verify collaborator exists
            cur.execute("SELECT id, nome, dia_fechamento FROM colaborador WHERE id = %s", (id,))
            colaborador = cur.fetchone()
            if not colaborador:
                return _error_response('Colaborador não encontrado', 'NOT_FOUND', 404)

            if request.method == 'PUT':
                data = request.get_json()
                if not data:
                    return _error_response('Dados JSON inválidos', 'INVALID_JSON')

                nome = data.get('nome', '').strip()
                dia_fechamento = data.get('dia_fechamento')

                if not nome or dia_fechamento is None:
                    return _error_response('nome e dia_fechamento são obrigatórios', 'MISSING_FIELDS')

                try:
                    dia = int(dia_fechamento)
                    if not (1 <= dia <= 31):
                        return _error_response('dia_fechamento deve estar entre 1 e 31', 'INVALID_DAY')
                except (ValueError, TypeError):
                    return _error_response('dia_fechamento deve ser um número', 'INVALID_DAY')

                cur.execute(
                    "UPDATE colaborador SET nome = %s, dia_fechamento = %s WHERE id = %s",
                    (nome, dia, id)
                )
                return _success_response({"message": "Colaborador atualizado com sucesso"})

            else:  # DELETE
                # NOVA VALIDAÇÃO: verificar despesas vinculadas
                cur.execute("SELECT COUNT(*) FROM despesa WHERE colaborador_id = %s", (id,))
                if cur.fetchone()[0] > 0:
                    return _error_response(
                        "Não é possível excluir: colaborador possui despesas cadastradas",
                        'HAS_EXPENSES',
                        409
                    )

                # NOVA VALIDAÇÃO: verificar rendas vinculadas
                cur.execute("SELECT COUNT(*) FROM renda_mensal WHERE colaborador_id = %s", (id,))
                if cur.fetchone()[0] > 0:
                    return _error_response(
                        "Não é possível excluir: colaborador possui rendas cadastradas",
                        'HAS_INCOMES',
                        409
                    )

                # Pode deletar
                cur.execute("DELETE FROM colaborador WHERE id = %s", (id,))
                return _success_response({"message": "Colaborador excluído com sucesso"})

    except Exception as e:
        logger.error(f"Erro em colaborador_por_id (id={id}): {str(e)}", exc_info=True)
        return _error_response('Erro interno no servidor', 'OPERATION_FAILED', 500)