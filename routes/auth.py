# routes/auth.py
"""
Authentication routes for Controle Financeiro Familiar API.

Security features:
- Password hashing with werkzeug (PBKDF2)
- Input validation (email, username, password strength)
- JWT token generation with claims
- Standardized error responses
- Token blacklist for logout (in-memory, Redis recommended for production)
"""
import re
import logging
from datetime import timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request
)
from werkzeug.security import generate_password_hash, check_password_hash

from connection import get_db_connection, get_db_cursor
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# In-memory token blacklist (use Redis in production)
_token_blacklist: set[str] = set()


def _add_to_blacklist(jti: str) -> None:
    """Add token JTI to blacklist."""
    _token_blacklist.add(jti)


def _is_blacklisted(jti: str) -> bool:
    """Check if token JTI is blacklisted."""
    return jti in _token_blacklist


def _validate_email(email: str) -> bool:
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def _validate_username(username: str) -> tuple[bool, str | None]:
    """Validate username format and length."""
    if not username:
        return False, "Username é obrigatório"
    if len(username) < 3:
        return False, "Username deve ter pelo menos 3 caracteres"
    if len(username) > 30:
        return False, "Username deve ter no máximo 30 caracteres"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username deve conter apenas letras, números, _ ou -"
    return True, None


def _validate_password(password: str) -> tuple[bool, str | None]:
    """Validate password strength."""
    if not password:
        return False, "Senha é obrigatória"
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    if len(password) > 128:
        return False, "Senha deve ter no máximo 128 caracteres"
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password):
        return False, "Senha deve conter pelo menos uma letra"
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    return True, None


def _error_response(message: str, code: str, status: int = 400) -> tuple:
    """Standardized error response."""
    return jsonify({'error': message, 'code': code}), status


def _success_response(data: dict, status: int = 200) -> tuple:
    """Standardized success response."""
    return jsonify(data), status


# ─── REGISTRO ─────────────────────────────────────────────
@auth_bp.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    if not data:
        return _error_response('Dados JSON inválidos', 'INVALID_JSON')

    username = data.get('username', '').strip()
    email = data.get('email', '').strip() if data.get('email') else ''
    password = data.get('password', '')

    # Validate username
    valid, msg = _validate_username(username)
    if not valid:
        return _error_response(msg, 'INVALID_USERNAME')

    # Validate email (optional but if provided must be valid)
    if email and not _validate_email(email):
        return _error_response('Formato de e-mail inválido', 'INVALID_EMAIL')

    # Validate password
    valid, msg = _validate_password(password)
    if not valid:
        return _error_response(msg, 'WEAK_PASSWORD')

    # Hash password
    password_hash = generate_password_hash(password)

    try:
        with get_db_cursor() as cur:
            cur.execute("""
                INSERT INTO usuario (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (username, email if email else None, password_hash))
            user_id = cur.fetchone()['id']

        logger.info(f"Usuário registrado: {username} (id={user_id})")
        return _success_response({
            'message': 'Usuário criado com sucesso',
            'user_id': user_id
        }, 201)

    except Exception as e:
        # Check for unique constraint violations
        error_msg = str(e).lower()
        if 'username' in error_msg:
            return _error_response('Username já existe', 'USERNAME_EXISTS', 409)
        elif 'email' in error_msg:
            return _error_response('E-mail já cadastrado', 'EMAIL_EXISTS', 409)
        logger.error(f"Erro ao registrar usuário: {e}")
        return _error_response('Erro interno ao criar conta', 'REGISTRATION_FAILED', 500)


# ─── LOGIN ───────────────────────────────────────────────
@auth_bp.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    if not data:
        return _error_response('Dados não fornecidos', 'MISSING_DATA')

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return _error_response('Usuário e senha são obrigatórios', 'MISSING_CREDENTIALS')

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM usuario WHERE username = %s AND ativo = true", (username,))
                user = cur.fetchone()

        if not user or not check_password_hash(user['password_hash'], password):
            logger.warning(f"Tentativa de login falhada para: {username}")
            return _error_response('Credenciais inválidas', 'INVALID_CREDENTIALS', 401)

        # Create access token with user claims
        access_token = create_access_token(
            identity=str(user['id']),
            additional_claims={'username': user['username']},
            expires_delta=timedelta(hours=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1))
        )

        logger.info(f"Login bem-sucedido: {username} (id={user['id']})")
        return _success_response({
            'access_token': access_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        })

    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return _error_response('Erro interno no servidor', 'LOGIN_FAILED', 500)


# ─── STATUS (VERIFICAR SE LOGADO) ────────────────────────
@auth_bp.route('/auth/status', methods=['GET'])
@jwt_required()
def auth_status():
    """Verify current token validity and return user info."""
    try:
        current_user_id = get_jwt_identity()
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, username, email FROM usuario WHERE id = %s AND ativo = true", (current_user_id,))
                user = cur.fetchone()

        if not user:
            return _error_response('Usuário não encontrado ou inativo', 'USER_NOT_FOUND', 401)

        return _success_response({
            'logged_in': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        })

    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        return _error_response('Erro interno', 'STATUS_FAILED', 500)


# ─── LOGOUT ──────────────────────────────────────────────
@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout - adds token to blacklist."""
    try:
        jti = get_jwt()['jti']
        _add_to_blacklist(jti)
        logger.info(f"Token revogado (jti={jti[:8]}...)")
        return _success_response({'message': 'Logout bem-sucedido'})
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        return _error_response('Erro interno', 'LOGOUT_FAILED', 500)


# ─── TOKEN REFRESH (OPTIONAL) ────────────────────────────
@auth_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Generate new access token using refresh token."""
    try:
        current_user_id = get_jwt_identity()
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT username FROM usuario WHERE id = %s AND ativo = true", (current_user_id,))
                user = cur.fetchone()

        if not user:
            return _error_response('Usuário não encontrado', 'USER_NOT_FOUND', 401)

        access_token = create_access_token(
            identity=str(current_user_id),
            additional_claims={'username': user['username']},
            expires_delta=timedelta(hours=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1))
        )

        return _success_response({'access_token': access_token})

    except Exception as e:
        logger.error(f"Erro ao renovar token: {e}")
        return _error_response('Erro interno', 'REFRESH_FAILED', 500)


# ─── BLACKLIST CHECK (used by JWT) ───────────────────────
@auth_bp.record_once
def _load_jwt_blacklist_check(state):
    """Register token blacklist callback with JWT manager."""
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(state.app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return _is_blacklisted(jti)