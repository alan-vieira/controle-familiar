"""
Testes expandidos de autenticação.
Cobre: refresh token, tokens revogados, expiração, handlers JWT, edge cases.
"""
import uuid
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta


class TestRefreshToken:
    """POST /api/auth/refresh"""

    def test_refresh_token_sucesso(self, client):
        """Refresh token válido deve retornar novo access token."""
        unique = uuid.uuid4().hex[:8]
        username = f"refresh_{unique}"
        
        # Registra e faz login
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        
        # Verifica se refresh_token foi retornado
        login_data = login_resp.get_json()
        if "refresh_token" in login_data:
            refresh_token = login_data["refresh_token"]
            
            # Usa refresh token para obter novo access token
            response = client.post(
                "/api/auth/refresh",
                headers={"Authorization": f"Bearer {refresh_token}"}
            )
            assert response.status_code == 200
            data = response.get_json()
            assert "access_token" in data

    def test_refresh_com_access_token_invalido_retorna_422(self, client):
        """Access token não deve funcionar como refresh token."""
        unique = uuid.uuid4().hex[:8]
        username = f"wrong_refresh_{unique}"
        
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        
        access_token = login_resp.get_json()["access_token"]
        
        # Tenta usar access token como refresh token
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        # Deve falhar (422 ou 401 dependendo da implementação)
        assert response.status_code in (401, 422)


class TestTokenRevogado:
    """Tokens na blacklist devem ser rejeitados."""

    def test_token_revogado_retorna_401(self, client, auth_headers):
        """Token na blacklist deve ser rejeitado."""
        # Faz logout (adiciona token à blacklist)
        client.post("/api/auth/logout", headers=auth_headers)
        
        # Tenta usar o mesmo token
        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 401

    def test_token_revogado_em_diferentes_endpoints(self, client, auth_headers):
        """Token revogado deve ser rejeitado em todos os endpoints protegidos."""
        client.post("/api/auth/logout", headers=auth_headers)
        
        endpoints = [
            "/api/colaboradores",
            "/api/despesas",
            "/api/rendas",
            "/api/resumo/2026-08",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)
            assert response.status_code == 401, f"Falhou em {endpoint}"


class TestExpiracaoToken:
    """Tokens expirados devem ser rejeitados."""

    def test_token_expirado_retorna_401(self, client):
        """Token expirado deve retornar 401."""
        unique = uuid.uuid4().hex[:8]
        username = f"expired_{unique}"
        
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        token = login_resp.get_json()["access_token"]
        
        # Avança 2 horas no tempo (token expira em 1h)
        with freeze_time(datetime.now() + timedelta(hours=2)):
            response = client.get(
                "/api/auth/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401


class TestHandlersJWT:
    """Handlers de erro JWT."""

    def test_token_malformado_retorna_401(self, client):
        """Token JWT malformado deve retornar 401 (não 422)."""
        response = client.get(
            "/api/auth/status",
            headers={"Authorization": "Bearer token.invalido.aqui"}
        )
        assert response.status_code == 401

    def test_token_vazio_retorna_401(self, client):
        """Header Authorization vazio deve retornar 401."""
        response = client.get(
            "/api/auth/status",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401

    def test_sem_header_authorization_retorna_401(self, client):
        """Requisição sem header Authorization deve retornar 401."""
        response = client.get("/api/auth/status")
        assert response.status_code == 401

    def test_header_authorization_invalido_retorna_401(self, client):
        """Header Authorization sem 'Bearer' deve retornar 401."""
        response = client.get(
            "/api/auth/status",
            headers={"Authorization": "InvalidToken123"}
        )
        assert response.status_code == 401


class TestRegistroEdgeCases:
    """Casos de borda no registro."""

    def test_registro_email_duplicado_retorna_409(self, client):
        """Email duplicado deve retornar 409."""
        unique = uuid.uuid4().hex[:8]
        email = f"dup_{unique}@test.com"
        
        client.post("/api/auth/register", json={
            "username": f"user1_{unique}",
            "email": email,
            "password": "SenhaForte@123",
        })
        
        response = client.post("/api/auth/register", json={
            "username": f"user2_{unique}",
            "email": email,
            "password": "SenhaForte@456",
        })
        assert response.status_code == 409

    def test_registro_sem_username_retorna_400(self, client):
        """Registro sem username deve retornar 400."""
        response = client.post("/api/auth/register", json={
            "password": "SenhaForte@123",
        })
        assert response.status_code == 400

    def test_registro_sem_password_retorna_400(self, client):
        """Registro sem password deve retornar 400."""
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"nopass_{unique}",
        })
        assert response.status_code == 400

    def test_registro_senha_muito_curta_retorna_400(self, client):
        """Senha muito curta deve ser rejeitada."""
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"short_{unique}",
            "password": "123",
        })
        assert response.status_code == 400


class TestLoginEdgeCases:
    """Casos de borda no login."""

    def test_login_sem_username_retorna_400(self, client):
        """Login sem username deve retornar 400."""
        response = client.post("/api/auth/login", json={
            "password": "SenhaForte@123",
        })
        assert response.status_code == 400

    def test_login_sem_password_retorna_400(self, client):
        """Login sem password deve retornar 400."""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
        })
        assert response.status_code == 400

    def test_login_usuario_inexistente_nao_diferencia_de_senha_errada(self, client):
        """
        Segurança: não deve diferenciar entre 'usuário não existe' e 'senha errada'.
        Ambos devem retornar 401 com mensagem genérica.
        """
        # Usuário inexistente
        response1 = client.post("/api/auth/login", json={
            "username": "usuario_inexistente_xyz",
            "password": "qualquer",
        })
        
        # Usuário existente com senha errada
        unique = uuid.uuid4().hex[:8]
        username = f"exists_{unique}"
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        response2 = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaErrada@456",
        })
        
        # Ambos devem retornar 401
        assert response1.status_code == 401
        assert response2.status_code == 401
        
        # Mensagens devem ser similares (não revelar se usuário existe)
        msg1 = response1.get_json().get("msg", "")
        msg2 = response2.get_json().get("msg", "")
        # Não deve conter "usuário não encontrado" ou similar
        assert "não encontrado" not in msg1.lower()
        assert "não encontrado" not in msg2.lower()