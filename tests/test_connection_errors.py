"""
Testes de edge cases e normalização em connection.py.
"""
import pytest


class TestNormalizeDatabaseUrl:
    """Testes da função de normalização de URL."""

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


class TestClosePool:
    """Testes do fechamento do pool."""

    @pytest.mark.skip(reason="Fecha pool global e quebra outros testes - executar isoladamente se necessário")
    def test_close_pool_libera_recursos(self, app):
        """close_pool() deve fechar o pool e resetar variável global."""
        from connection import get_pool, close_pool
        
        with app.app_context():
            pool = get_pool()
            assert pool is not None
            
            close_pool()
            
            # Verifica que a variável global foi resetada
            from connection import _pool as pool_after
            assert pool_after is None
            
            # Tenta usar novamente - deve criar novo pool (lazy init)
            from connection import get_pool as get_pool_fresh
            new_pool = get_pool_fresh()
            assert new_pool is not None


class TestPoolErrorHandling:
    """Testes de tratamento de erros no pool."""

    def test_get_pool_sem_database_url_levanta_erro(self):
        """get_pool() deve levantar erro se DATABASE_URL não configurada."""
        import os
        from connection import _pool, _get_pool
        
        # Salva URL original
        original_url = os.environ.get('DATABASE_URL')
        
        try:
            # Remove DATABASE_URL
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
            
            # Reseta pool global
            import connection
            connection._pool = None
            
            with pytest.raises(RuntimeError) as exc_info:
                _get_pool()
            
            assert "DATABASE_URL não configurada" in str(exc_info.value)
        finally:
            # Restaura
            if original_url:
                os.environ['DATABASE_URL'] = original_url
            connection._pool = None

    def test_normalize_database_url_com_sslmode(self):
        """URL com sslmode deve ser preservada."""
        from connection import _normalize_database_url
        
        url = "postgresql://user:***@host:5432/db?sslmode=require"
        result = _normalize_database_url(url)
        assert result == "postgresql://user:***@host:5432/db?sslmode=require"

    def test_normalize_database_url_sem_scheme(self):
        """URL sem scheme deve ser tratada."""
        from connection import _normalize_database_url
        
        url = "host:5432/db"
        result = _normalize_database_url(url)
        assert result == "host:5432/db"


class TestInitDbErrorHandling:
    """Testes de tratamento de erros em init_db."""

    def test_init_db_retorna_false_em_erro(self, app):
        """init_db() deve retornar False em caso de erro (não crash)."""
        from connection import init_db
        from unittest.mock import patch
        
        with app.app_context():
            # Mock para simular erro na criação de tabela
            with patch('connection.get_db_cursor') as mock_cursor:
                mock_cursor.side_effect = Exception("Erro simulado")
                
                result = init_db()
                assert result is False


class TestGetDbConnectionEdgeCases:
    """Edge cases do context manager get_db_connection."""

    def test_conexao_fechada_apos_excecao(self, app):
        """Conexão deve ser devolvida ao pool mesmo após exceção."""
        from connection import get_db_connection
        
        with app.app_context():
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    raise ValueError("Erro simulado")
            except ValueError:
                pass
            
            # Se chegou aqui sem deadlock, pool funcionou
            # Tenta usar novamente
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result is not None

    def test_rollback_chamado_em_excecao(self, app):
        """Rollback deve ser chamado mesmo se conexão estiver quebrada."""
        from connection import get_db_connection
        from unittest.mock import patch, MagicMock
        
        with app.app_context():
            with patch('connection.get_pool') as mock_pool:
                mock_conn = MagicMock()
                mock_conn.rollback.side_effect = Exception("Conn broken")
                mock_pool.return_value.getconn.return_value = mock_conn
                mock_pool.return_value.putconn = MagicMock()
                
                try:
                    with get_db_connection() as conn:
                        raise ValueError("Erro simulado")
                except ValueError:
                    pass
                
                # putconn deve ser chamado mesmo com erro no rollback
                mock_pool.return_value.putconn.assert_called_once()


class TestThreadSafetyEdgeCases:
    """Testes adicionais de thread safety."""

    def test_multiplas_threads_sem_deadlock(self, app):
        """Múltiplas threads devem conseguir conexões sem deadlock."""
        from connection import get_db_connection
        import threading
        
        results = []
        errors = []
        
        def worker():
            try:
                with app.app_context():
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT 1")
                        results.append(True)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        
        assert len(errors) == 0
        assert len(results) == 10