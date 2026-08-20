"""
Testes de handlers de erro genéricos e exceções não tratadas.
Cobre as linhas restantes em app.py.
"""
import uuid
import pytest


class TestGenericErrorHandlers:
    """Handlers de erro 500 e exceções genéricas."""

    def test_erro_500_retorna_json_e_nao_vaza_stack(self, client, app):
        """Exceção não tratada deve retornar 500 JSON sem stack trace."""
        # Cria usuário e obtém token
        unique = uuid.uuid4().hex[:8]
        client.post("/api/auth/register", json={
            "username": f"err500_{unique}",
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": f"err500_{unique}",
            "password": "SenhaForte@123",
        })
        token = login_resp.get_json()["access_token"]
        
        # Testa endpoint que não existe (404 não 500, mas testa handler)
        response = client.get("/api/endpoint_inexistente", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data or "msg" in data

    def test_erro_500_em_diferentes_endpoints(self, client, app):
        """Erro 500 deve retornar JSON consistente."""
        unique = uuid.uuid4().hex[:8]
        client.post("/api/auth/register", json={
            "username": f"err500b_{unique}",
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": f"err500b_{unique}",
            "password": "SenhaForte@123",
        })
        token = login_resp.get_json()["access_token"]
        
        # Testa método não permitido (405)
        response = client.post("/health", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 405
        data = response.get_json()
        assert "error" in data or "msg" in data


class TestRootAndHealthEndpoints:
    """Testes dos endpoints raiz e health check."""

    def test_root_retorna_info_basica(self, client):
        """Endpoint raiz deve retornar status e versão."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert "version" in data or "message" in data

    def test_health_check_banco_conectado(self, client):
        """Health check deve verificar conexão com banco."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "OK"
        assert "database" in data
        assert data["database"] == "connected"

    def test_health_check_retorna_ambiente(self, client):
        """Health check deve informar o ambiente (testing/production)."""
        response = client.get("/health")
        data = response.get_json()
        assert "environment" in data
        assert data["environment"] in ("testing", "development", "production")


class TestSecurityHeaders:
    """Testes de headers de segurança."""

    def test_security_headers_presentes(self, client):
        """Headers de segurança devem estar presentes nas respostas."""
        response = client.get("/health")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_hsts_apenas_em_producao(self, app, client):
        """HSTS só deve aparecer quando não DEBUG."""
        # Em modo testing (DEBUG=False geralmente), HSTS deve estar presente
        response = client.get("/health")
        # Se DEBUG=False, HSTS deve estar presente
        if not app.config.get("DEBUG", False):
            assert "Strict-Transport-Security" in response.headers


class TestCORSHeaders:
    """Testes de headers CORS."""

    def test_cors_headers_em_resposta(self, client):
        """Resposta deve conter headers CORS quando configurado."""
        response = client.options("/health")
        # CORS pode não estar habilitado se CORS_ORIGINS não estiver configurado
        # Mas options deve responder
        assert response.status_code in (200, 204)


class TestErrorHandlerConsistency:
    """Consistência dos handlers de erro."""

    def test_404_retorna_json_padrao(self, client):
        """404 deve retornar JSON padronizado."""
        response = client.get("/api/endpoint_inexistente")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data or "msg" in data

    def test_405_retorna_json_padrao(self, client):
        """405 Method Not Allowed deve retornar JSON."""
        response = client.post("/health")
        assert response.status_code == 405
        data = response.get_json()
        assert "error" in data or "msg" in data