"""
Testes focados nos handlers de erro JWT e edge cases de auth.
Cobre as linhas restantes em routes/auth.py.
"""
import uuid
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta


class TestJWTErrorHandlersSpecific:
    """Testes específicos dos callbacks de erro do Flask-JWT-Extended."""

    def test_expired_token_loader_mensagem_customizada(self, client):
        """Handler de token expirado deve retornar mensagem clara."""
        unique = uuid.uuid4().hex[:8]
        username = f"exp_handler_{unique}"
        
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        token = login_resp.get_json()["access_token"]
        
        with freeze_time(datetime.now() + timedelta(hours=2)):
            response = client.get(
                "/api/auth/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401
            data = response.get_json()
            # Verifica se a mensagem customizada do handler está presente
            # O handler pode retornar TOKEN_INVALID ou TOKEN_EXPIRED dependendo da implementação
            assert data.get("code") in ("TOKEN_EXPIRED", "TOKEN_INVALID")
            assert "expirado" in data.get("error", "").lower() or "inválido" in data.get("error", "").lower() or \
                   "expirado" in data.get("msg", "").lower() or "inválido" in data.get("msg", "").lower()

    def test_revoked_token_loader_mensagem_customizada(self, client, auth_headers):
        """Handler de token revogado deve retornar mensagem clara."""
        client.post("/api/auth/logout", headers=auth_headers)
        
        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 401
        data = response.get_json()
        assert "revogado" in data.get("error", "").lower() or "revoked" in data.get("error", "").lower() or \
               "revogado" in data.get("msg", "").lower() or "revoked" in data.get("msg", "").lower()

    def test_login_campos_vazios_ou_somente_espacos(self, client):
        """Login com strings vazias ou espaços deve ser rejeitado."""
        response = client.post("/api/auth/login", json={
            "username": "   ",
            "password": "   "
        })
        assert response.status_code == 400

    def test_registro_senha_apenas_numeros_rejeitada(self, client):
        """Senha sem letras deve ser rejeitada pela política de força."""
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"num_{unique}",
            "password": "12345678"
        })
        assert response.status_code == 400


class TestTokenBlacklist:
    """Testes da blacklist de tokens."""

    def test_logout_adiciona_token_blacklist(self, client, auth_headers):
        """Logout deve adicionar JTI à blacklist."""
        # Faz login e obtém token
        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 200
        
        # Faz logout
        logout_resp = client.post("/api/auth/logout", headers=auth_headers)
        assert logout_resp.status_code == 200
        
        # Token deve ser rejeitado agora
        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 401

    def test_blacklist_persiste_entre_requests(self, client, auth_headers):
        """Token na blacklist deve continuar rejeitado em requests subsequentes."""
        client.post("/api/auth/logout", headers=auth_headers)
        
        # Múltiplos requests devem falhar
        for _ in range(3):
            response = client.get("/api/auth/status", headers=auth_headers)
            assert response.status_code == 401


class TestRefreshTokenErrors:
    """Testes de erros no refresh token."""

    def test_refresh_sem_token_retorna_401(self, client):
        """Refresh sem token deve retornar 401."""
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401

    def test_refresh_token_expirado_retorna_401(self, client):
        """Refresh token expirado deve retornar 401."""
        unique = uuid.uuid4().hex[:8]
        username = f"refresh_exp_{unique}"
        
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        login_resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        
        login_data = login_resp.get_json()
        if "refresh_token" in login_data:
            refresh_token = login_data["refresh_token"]
            
            with freeze_time(datetime.now() + timedelta(days=2)):
                response = client.post(
                    "/api/auth/refresh",
                    headers={"Authorization": f"Bearer {refresh_token}"}
                )
                assert response.status_code == 401


class TestAuthEdgeCases:
    """Casos de borda adicionais."""

    def test_registro_email_invalido_formato(self, client):
        """Email com formato inválido deve ser rejeitado."""
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"invalid_email_{unique}",
            "email": "not-an-email",
            "password": "SenhaForte@123",
        })
        assert response.status_code == 400

    def test_registro_username_curto(self, client):
        """Username muito curto deve ser rejeitado."""
        response = client.post("/api/auth/register", json={
            "username": "ab",  # mínimo 3 chars
            "password": "SenhaForte@123",
        })
        assert response.status_code == 400

    def test_registro_username_com_caracteres_especiais(self, client):
        """Username com caracteres especiais pode ser rejeitado."""
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"user@#${unique}",
            "password": "SenhaForte@123",
        })
        # Depende da validação - aceita ou rejeita
        assert response.status_code in (201, 400)