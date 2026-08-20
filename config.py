# config.py
"""
Configuration management for Controle Financeiro Familiar API.

Supports three environments: development, production, and testing.
All required variables must be set via environment variables — no insecure fallbacks.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins(value: str | None) -> list[str]:
    """Parse comma-separated CORS origins from environment variable."""
    if not value:
        return []
    return [origin.strip() for origin in value.split(',') if origin.strip()]


def _get_required_env(key: str) -> str:
    """Get required environment variable or raise an error."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Variável de ambiente obrigatória não definida: {key}")
    return value


class Config:
    """Base configuration with shared settings."""

    # Flask
    SECRET_KEY: str = _get_required_env('SECRET_KEY')
    JWT_SECRET_KEY: str = _get_required_env('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES_HOURS: int = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', '1'))

    # Database
    DATABASE_URL: str = _get_required_env('DATABASE_URL')
    DATABASE_SSLMODE: str = os.getenv('DATABASE_SSLMODE', 'require')
    DATABASE_POOL_MAX: int = int(os.getenv('DATABASE_POOL_MAX', '10'))

    # CORS
    CORS_ORIGINS: list[str] = _parse_cors_origins(os.getenv('CORS_ORIGINS'))

    # Security headers
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'

    @classmethod
    def validate(cls) -> None:
        """Validate all required configuration is present."""
        required = ['SECRET_KEY', 'JWT_SECRET_KEY', 'DATABASE_URL']
        missing = [key for key in required if not getattr(cls, key, None)]
        if missing:
            raise ValueError(f"Configurações obrigatórias ausentes: {', '.join(missing)}")

        if not cls.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS deve conter pelo menos uma origem permitida")

        if cls.JWT_ACCESS_TOKEN_EXPIRES_HOURS <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRES_HOURS deve ser maior que zero")

        if cls.DATABASE_POOL_MAX <= 0:
            raise ValueError("DATABASE_POOL_MAX deve ser maior que zero")


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG: bool = True
    TESTING: bool = False
    SESSION_COOKIE_SECURE: bool = False  # Allow HTTP in development


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG: bool = False
    TESTING: bool = False
    SESSION_COOKIE_SECURE: bool = True

    @classmethod
    def validate(cls) -> None:
        super().validate()
        # Extra production checks
        if cls.SECRET_KEY == 'sua_chave_secreta_aleatoria_segura':
            raise ValueError("SECRET_KEY insegura detectada — configure uma chave forte em produção")
        if len(cls.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres em produção")


class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG: bool = True
    TESTING: bool = True
    SESSION_COOKIE_SECURE: bool = False

    # Override with test-specific values if needed
    DATABASE_URL: str = os.getenv('TEST_DATABASE_URL', _get_required_env('DATABASE_URL'))
    DATABASE_POOL_MAX: int = 2

    # Disable rate limiting in tests
    RATELIMIT_ENABLED: bool = False


def get_config() -> type[Config]:
    """Return the appropriate config class based on FLASK_ENV."""
    env = os.getenv('FLASK_ENV', 'development').lower()
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }
    config_class = configs.get(env)
    if not config_class:
        raise ValueError(f"FLASK_ENV inválido: '{env}'. Use: development, production, ou testing")
    return config_class


# For backward compatibility — expose validated config instance
try:
    CurrentConfig = get_config()
    CurrentConfig.validate()
except ValueError as e:
    # Defer validation error to app startup for clearer messaging
    class _DeferredConfig:
        def __getattr__(self, name):
            raise RuntimeError(f"Configuração inválida: {e}")

    CurrentConfig = _DeferredConfig()