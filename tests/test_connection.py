"""
Testes do connection.py: pool, rollback, context managers.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import date


class TestGetDbConnection:
    """get_db_connection() context manager."""

    def test_conexao_retornada_ao_pool(self, app):
        """Conexão deve ser devolvida ao pool após uso."""
        from connection import get_db_connection
        
        with app.app_context():
            with get_db_connection() as conn:
                assert conn is not None
            # Após o context, conexão deve ser devolvida ao pool
            # (não podemos testar diretamente, mas verificamos que não há erro)

    def test_rollback_em_excecao(self, app):
        """Exceção dentro do context deve causar rollback."""
        from connection import get_db_connection
        
        with app.app_context():
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO usuario (username, password_hash) VALUES ('test_rollback', 'hash')")
                    raise ValueError("Erro simulado")
            except ValueError:
                pass
            
            # Verifica que o usuário não foi inserido (rollback funcionou)
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM usuario WHERE username = 'test_rollback'")
                count = cur.fetchone()['count']
                assert count == 0


class TestGetDbCursor:
    """get_db_cursor() context manager."""

    def test_cursor_com_commit(self, app):
        """Cursor com commit deve persistir dados."""
        from connection import get_db_cursor
        
        with app.app_context():
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO usuario (username, password_hash) VALUES (%s, %s)",
                    ("test_commit", "hash")
                )
            
            # Verifica que foi inserido
            with get_db_cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM usuario WHERE username = 'test_commit'")
                count = cur.fetchone()['count']
                assert count == 1
            
            # Limpa
            with get_db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM usuario WHERE username = 'test_commit'")

    def test_cursor_sem_commit_nao_persiste(self, app):
        """Cursor sem commit não deve persistir dados."""
        from connection import get_db_cursor
        
        with app.app_context():
            with get_db_cursor(commit=False) as cur:
                cur.execute(
                    "INSERT INTO usuario (username, password_hash) VALUES (%s, %s)",
                    ("test_no_commit", "hash")
                )
            
            # Verifica que NÃO foi inserido
            with get_db_cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM usuario WHERE username = 'test_no_commit'")
                count = cur.fetchone()['count']
                assert count == 0


class TestPoolConnections:
    """Pool de conexões."""

    def test_pool_criado_na_inicializacao(self, app):
        """Pool deve ser criado quando app é inicializada."""
        from connection import get_pool
        
        with app.app_context():
            pool = get_pool()
            assert pool is not None

    def test_pool_retorna_conexoes(self, app):
        """Pool deve retornar conexões válidas."""
        from connection import get_pool
        
        with app.app_context():
            pool = get_pool()
            conn = pool.getconn()
            assert conn is not None
            pool.putconn(conn)


class TestInitDb:
    """init_db() - criação do schema."""

    def test_init_db_cria_tabelas(self, app):
        """init_db() deve criar todas as tabelas necessárias."""
        from connection import get_db_cursor
        
        with app.app_context():
            # Verifica que as tabelas existem
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row['table_name'] for row in cur.fetchall()]
                
                # Tabelas essenciais
                assert "usuario" in tables
                assert "colaborador" in tables
                assert "despesa" in tables
                assert "renda_mensal" in tables

    def test_init_db_idempotente(self, app):
        """init_db() deve ser idempotente (pode chamar múltiplas vezes)."""
        from connection import init_db, get_db_cursor
        
        with app.app_context():
            # Primeira chamada
            result1 = init_db()
            assert result1 is True
            
            # Segunda chamada
            result2 = init_db()
            assert result2 is True
            
            # Tabelas devem continuar existindo
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row['table_name'] for row in cur.fetchall()]
                assert "usuario" in tables


class TestAdapters:
    """Adapters psycopg2 - Decimal."""

    def test_decimal_adapter_registrado(self, app):
        """Adapter Decimal deve estar registrado e funcionar."""
        from connection import get_db_cursor
        
        with app.app_context():
            # Cria colaborador de teste
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO colaborador (nome, dia_fechamento) VALUES (%s, %s) RETURNING id",
                    ("Test Adapter", 5)
                )
                colab_id = cur.fetchone()['id']
                
                # Insere despesa com Decimal (incluindo mes_vigente calculado)
                from utils.date_utils import calcular_mes_vigente
                mes_vigente = calcular_mes_vigente(date(2026, 8, 15), "pix", 5)
                cur.execute(
                    """INSERT INTO despesa 
                    (data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (date(2026, 8, 15), mes_vigente, "Test Decimal", Decimal("123.45"), "pix", colab_id, "alimentacao")
                )
                
                # Verifica que foi inserido corretamente
                cur.execute(
                    "SELECT valor FROM despesa WHERE descricao = 'Test Decimal'"
                )
                valor = cur.fetchone()['valor']
                assert valor == Decimal("123.45")
                
                # Limpa
                cur.execute("DELETE FROM despesa WHERE descricao = 'Test Decimal'")
                cur.execute("DELETE FROM colaborador WHERE id = %s", (colab_id,))


class TestNormalizeDatabaseUrl:
    """_normalize_database_url() function."""

    def test_normalize_postgres_to_postgresql(self):
        """postgres:// deve ser convertido para postgresql://."""
        from connection import _normalize_database_url
        
        url = "postgres://user:***@host:5432/db"
        result = _normalize_database_url(url)
        assert result == "postgresql://user:***@host:5432/db"

    def test_normalize_postgresql_unchanged(self):
        """postgresql:// deve permanecer inalterado."""
        from connection import _normalize_database_url
        
        url = "postgresql://user:***@host:5432/db"
        result = _normalize_database_url(url)
        assert result == "postgresql://user:***@host:5432/db"

    def test_normalize_other_unchanged(self):
        """Outras URLs devem permanecer inalteradas."""
        from connection import _normalize_database_url
        
        url = "mysql://user:***@host:3306/db"
        result = _normalize_database_url(url)
        assert result == "mysql://user:***@host:3306/db"


class TestThreadSafety:
    """Testes básicos de thread safety do pool."""

    def test_multiplas_conexoes_simultaneas(self, app):
        """Pool deve suportar múltiplas conexões simultâneas."""
        from connection import get_db_connection
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                with app.app_context():
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT pg_sleep(0.1)")  # Simula trabalho
                        results.append(True)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 5