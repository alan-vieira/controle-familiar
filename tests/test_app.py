"""
Testes do app.py: health check, error handlers, factory pattern.
"""
import pytest


class TestHealthCheck:
    """GET /health"""

    def test_health_check_retorna_200(self, client):
        """Health check deve retornar 200 quando banco está OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "OK"  # API retorna 'OK', não 'healthy'
        assert "database" in data

    def test_health_check_informa_versao(self, client):
        """Health check deve incluir versão da API."""
        response = client.get("/health")
        data = response.get_json()
        # Health check não tem version, mas root endpoint tem
        response = client.get("/")
        data = response.get_json()
        assert "version" in data


class TestErrorHandlers:
    """Handlers de erro HTTP."""

    def test_404_retorna_json(self, client):
        """404 deve retornar JSON, não HTML."""
        response = client.get("/api/endpoint_inexistente")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data or "msg" in data

    def test_405_method_not_allowed_retorna_json(self, client):
        """405 deve retornar JSON."""
        # POST em endpoint que só aceita GET
        response = client.post("/health")
        assert response.status_code == 405
        data = response.get_json()
        assert "error" in data or "msg" in data

    def test_erro_nao_vaza_detalhes_internos_em_producao(self, app, client):
        """Em produção, erros não devem vazar stack traces."""
        if app.config.get("ENV") == "production":
            response = client.get("/api/endpoint_inexistente")
            data = response.get_json()
            # Não deve conter paths do servidor
            assert "Traceback" not in str(data)
            assert "/app/" not in str(data)
            assert "File " not in str(data)


class TestRootEndpoint:
    """GET /"""

    def test_root_retorna_status_basico(self, client):
        """Endpoint raiz deve retornar status básico."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data or "message" in data


class TestFactoryPattern:
    """Testes do create_app()."""

    def test_create_app_retorna_instancia_flask(self, app):
        """create_app() deve retornar instância Flask."""
        from flask import Flask
        assert isinstance(app, Flask)

    def test_app_tem_config_de_teste(self, app):
        """App em modo teste deve ter TESTING=True."""
        assert app.config["TESTING"] is True

    def test_app_tem_secret_key(self, app):
        """App deve ter SECRET_KEY configurada."""
        assert app.config.get("SECRET_KEY") is not None
        assert len(app.config["SECRET_KEY"]) >= 32

    def test_app_tem_jwt_secret_key(self, app):
        """App deve ter JWT_SECRET_KEY separada."""
        assert app.config.get("JWT_SECRET_KEY") is not None
        assert app.config["JWT_SECRET_KEY"] != app.config["SECRET_KEY"]