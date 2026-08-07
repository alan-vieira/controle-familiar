"""
Database connection pool management for PostgreSQL using psycopg2.

Provides thread-safe connection pooling with context managers for safe
connection handling, automatic rollback on errors, and proper cleanup.
"""
import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

# Global connection pool instance
_pool: Optional[ThreadedConnectionPool] = None


def _normalize_database_url(url: str) -> str:
    """
    Normalize database URL for psycopg2 compatibility.

    Converts 'postgres://' to 'postgresql://' if present.
    psycopg2 >= 2.8 accepts 'postgresql://' directly.
    """
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def _get_pool() -> ThreadedConnectionPool:
    """
    Get the global connection pool, initializing if needed (lazy initialization).

    Returns:
        ThreadedConnectionPool instance

    Raises:
        RuntimeError: If DATABASE_URL is not configured
        psycopg2.OperationalError: If connection to database fails
    """
    global _pool

    if _pool is not None:
        return _pool

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL não configurada nas variáveis de ambiente")

    # Normalize URL
    database_url = _normalize_database_url(database_url)

    # Get pool configuration from environment
    pool_max = int(os.environ.get('DATABASE_POOL_MAX', '10'))
    
    # Build connection parameters
    # If sslmode is already in the URL, don't override it
    connect_kwargs = {
        'dsn': database_url,
        'cursor_factory': RealDictCursor,
    }
    
    # Only add sslmode if not already in URL
    if 'sslmode=' not in database_url:
        sslmode = os.environ.get('DATABASE_SSLMODE', 'require')
        connect_kwargs['sslmode'] = sslmode

    try:
        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=pool_max,
            **connect_kwargs
        )
        return _pool
    except Exception as e:
        raise RuntimeError(f"Falha ao inicializar pool de conexões: {e}") from e


def get_pool() -> ThreadedConnectionPool:
    """
    Public interface to get the connection pool.
    
    This is the recommended way to access the pool.
    The pool is initialized lazily on first access.
    """
    return _get_pool()


def close_pool() -> None:
    """
    Close all connections in the pool.
    
    Should be called on application shutdown to cleanly release resources.
    """
    global _pool
    if _pool is not None:
        try:
            _pool.closeall()
        except Exception:
            pass  # Ignore errors during shutdown
        finally:
            _pool = None


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for acquiring a database connection from the pool.

    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()

    The connection is automatically returned to the pool on exit.
    On exception, transaction is rolled back before returning to pool.
    
    Yields:
        psycopg2.extensions.connection: Database connection from pool
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    except Exception:
        # Rollback on any exception to prevent transaction leaks
        try:
            conn.rollback()
        except Exception:
            pass  # Connection might be broken
        raise
    finally:
        # Always return connection to pool
        try:
            # Ensure no transaction is left open
            conn.rollback()
        except Exception:
            pass
        pool.putconn(conn)


@contextmanager
def get_db_cursor(commit: bool = True) -> Generator[RealDictCursor, None, None]:
    """
    Context manager for acquiring a cursor with automatic connection management.

    This is the most convenient way to execute queries. Handles connection
    acquisition, commit/rollback, and cleanup automatically.

    Usage:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM usuario WHERE id = %s", (user_id,))
            user = cur.fetchone()

        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT ...")
            # Caller must commit manually if needed

    Args:
        commit: If True (default), commit on success. If False, caller must commit.
        
    Yields:
        RealDictCursor: Database cursor for executing queries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def init_db(force: bool = False) -> bool:
    """
    Initialize database schema (basic setup only).

    Creates the minimum required tables if they don't exist.
    For production, use proper migration tools (Alembic, etc.).

    Args:
        force: If True, attempt to create tables even if they might exist.
               If False (default), uses CREATE TABLE IF NOT EXISTS.

    Returns:
        bool: True if initialization succeeded, False otherwise
        
    Note:
        This function is idempotent - safe to call multiple times.
        Tables are created with IF NOT EXISTS to avoid errors.
    """
    try:
        with get_db_cursor(commit=True) as cur:
            # usuario table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuario (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(150) NOT NULL UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ativo BOOLEAN DEFAULT true
                )
            ''')

            # colaborador table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS colaborador (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(150) NOT NULL,
                    dia_fechamento INTEGER NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # categoria table (optional - for future use)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS categoria (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    tipo VARCHAR(20) NOT NULL DEFAULT 'despesa',
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # despesa table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS despesa (
                    id SERIAL PRIMARY KEY,
                    data_compra DATE NOT NULL,
                    mes_vigente VARCHAR(7) NOT NULL,
                    descricao VARCHAR(255) NOT NULL,
                    valor NUMERIC(12, 2) NOT NULL CHECK (valor >= 0),
                    tipo_pg VARCHAR(20) NOT NULL,
                    colaborador_id INTEGER NOT NULL REFERENCES colaborador(id),
                    categoria VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # renda_mensal table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS renda_mensal (
                    id SERIAL PRIMARY KEY,
                    colaborador_id INTEGER NOT NULL REFERENCES colaborador(id),
                    mes_ano VARCHAR(7) NOT NULL,
                    valor NUMERIC(12, 2) NOT NULL CHECK (valor >= 0),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(colaborador_id, mes_ano)
                )
            ''')

            # divisao_mensal table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS divisao_mensal (
                    mes_ano VARCHAR(7) PRIMARY KEY,
                    paga BOOLEAN NOT NULL DEFAULT false,
                    data_acerto DATE,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # configuracao_fechamento table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS configuracao_fechamento (
                    id SERIAL PRIMARY KEY,
                    dia_fechamento INTEGER NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Ensure default configuracao_fechamento exists
            cur.execute('''
                INSERT INTO configuracao_fechamento (dia_fechamento)
                SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM configuracao_fechamento)
            ''')

        return True
        
    except Exception as e:
        # Log error but don't crash - app can still start
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao inicializar schema do banco: {e}")
        return False