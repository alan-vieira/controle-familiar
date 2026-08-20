"""
Controle Financeiro Familiar - Flask Application Factory.

Production-ready Flask application with:
- Application factory pattern
- Proper WSGI entry point (single app instance)
- Environment-driven configuration
- CORS with configurable origins
- JWT authentication
- Global error handling
- Health check endpoints
"""
import atexit
import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from config import get_config
from connection import close_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from routes.auth import is_token_blacklisted
from limiter import limiter

# Import blueprints
from routes.auth import auth_bp
from routes.colaboradores import colaboradores_bp
from routes.despesas import despesas_bp
from routes.rendas import rendas_bp
from routes.divisao import divisao_bp
from routes.resumo import resumo_bp


def create_app(config_class=None) -> Flask:
    """
    Application factory pattern.
    Creates and configures the Flask application instance.
    """
    if config_class is None:
        config_class = get_config()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    jwt = JWTManager(app)
    
    # ── Headers de segurança ─────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not getattr(config_class, 'DEBUG', False):
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )
        return response

    # ── Blocklist de tokens (logout) — registrada na factory ─────
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_blacklisted(jwt_payload['jti'])

    # ── Rate limiting ─────────────────────────────────────────────
        if not getattr(config_class, 'RATELIMIT_ENABLED', True):
            logger.info("Rate limiting disabled (RATELIMIT_ENABLED=False)")
        else:
            limiter.init_app(app)

    # CORS Configuration - from environment variable
    cors_origins = getattr(config_class, 'CORS_ORIGINS', [])
    if not cors_origins:
        logger.warning("CORS_ORIGINS não configurado - CORS desabilitado para segurança")

    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
        expose_headers=['Content-Range', 'X-Total-Count'],
        max_age=3600
    )

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token expirado', 'code': 'TOKEN_EXPIRED'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Token inválido', 'code': 'TOKEN_INVALID'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Token de autorização ausente', 'code': 'TOKEN_MISSING'}), 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token não renovado', 'code': 'TOKEN_NOT_FRESH'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token revogado', 'code': 'TOKEN_REVOKED'}), 401

    # Global error handlers
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        """Handle all HTTP exceptions with JSON response."""
        response = {
            'error': e.name,
            'message': e.description,
            'code': e.code
        }
        logger.warning(f"HTTP {e.code}: {e.name} - {request.path}")
        return jsonify(response), e.code

    @app.errorhandler(Exception)
    def handle_internal_error(e: Exception):
        """Handle unexpected internal server errors."""
        logger.exception(f"Erro interno não tratado: {request.path}")
        if getattr(config_class, 'DEBUG', False):
            return jsonify({
                'error': 'Internal Server Error',
                'message': str(e),
                'type': type(e).__name__
            }), 500
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Ocorreu um erro interno. Tente novamente mais tarde.'
        }), 500

    # Health check endpoints
    @app.route('/')
    def index():
        """Root endpoint - basic health check."""
        return jsonify({
            'status': 'healthy',
            'message': 'Controle Familiar API',
            'version': '0.3.0'
        })

    @app.route('/health')
    def health():
        """Detailed health check endpoint."""
        db_status = 'unknown'
        http_status = 200
        
        try:
            from connection import get_db_connection
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)[:100]}'
            http_status = 503  # Service Unavailable
            logger.error(f"Health check DB failed: {e}")

        return jsonify({
            'status': 'OK' if db_status == 'connected' else 'degraded',
            'database': db_status,
            'environment': config_class.__name__.replace('Config', '').lower()
        }), http_status

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')

    # Log registered routes in debug mode
    if getattr(config_class, 'DEBUG', False):
        logger.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            logger.info(f"  {rule.methods} {rule.rule}")

    return app


# WSGI entry point for Gunicorn/Render
# Create the application instance ONCE at module load time.
# This is the standard, robust way for WSGI servers.
application = create_app()
app = application  # Alias for compatibility

# Fecha o pool APENAS no shutdown do processo (nunca por request)
atexit.register(close_pool)


# For local development only - not used in production
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor de desenvolvimento na porta {port}")
    application.run(host='0.0.0.0', port=port, debug=True)