"""Testes de autenticação."""
import uuid
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta


class TestRegistro:
    def test_registro_sucesso(self, client):
        unique = uuid.uuid4().hex[:8]
        response = client.post("/api/auth/register", json={
            "username": f"newuser_{unique}",
            "email": f"new_{unique}@test.com",
            "password": "SenhaForte@123",
        })
        assert response.status_code == 201

    def test_registro_username_duplicado_retorna_409(self, client):
        unique = uuid.uuid4().hex[:8]
        payload = {"username": f"dup_{unique}", "password": "SenhaForte@123"}
        client.post("/api/auth/register", json=payload)
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 409


class TestLogin:
    def test_login_sucesso_retorna_token(self, client):
        unique = uuid.uuid4().hex[:8]
        username = f"login_{unique}"
        client.post("/api/auth/register", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        response = client.post("/api/auth/login", json={
            "username": username,
            "password": "SenhaForte@123",
        })
        assert response.status_code == 200
        assert client.get_cookie("access_token"), "Token não definido no cookie de resposta"
        assert "user" in response.get_json()


class TestLogoutEBlacklist:
    def test_logout_revoga_token(self, client, auth_headers):
        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 200

        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200

        response = client.get("/api/auth/status", headers=auth_headers)
        assert response.status_code == 401