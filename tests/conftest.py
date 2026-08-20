"""
Fixtures globais para a suite de testes do Controle Familiar.
Estratégia: PostgreSQL real via Docker com rollback por transação.
"""
import os
import pytest
import uuid
from datetime import date

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://test_user:test_password@localhost:5433/controle_familiar_test?sslmode=disable"
)

from app import create_app
from connection import get_db_connection, init_db


@pytest.fixture(scope="session")
def app():
    """Cria a aplicação Flask em modo de teste."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "JWT_ACCESS_TOKEN_EXPIRES_HOURS": 1,
        "RATELIMIT_ENABLED": False,
    })
    yield app


@pytest.fixture(scope="session", autouse=True)
def setup_database(app):
    """Garante que o schema está criado no início da sessão."""
    with app.app_context():
        init_db()
    yield


@pytest.fixture()
def db(app):
    """Conexão isolada por teste com rollback automático."""
    with app.app_context():
        with get_db_connection() as conn:
            try:
                cur = conn.cursor()
                cur.execute("BEGIN")
                yield conn
            finally:
                conn.rollback()


@pytest.fixture(autouse=True)
def clean_database(app, db):
    """Limpa todas as tabelas antes de cada teste para isolamento."""
    # As tabelas que podem ter dados residuais
    tables = [
        'token_blacklist', 'despesa', 'renda_mensal', 'divisao_mensal',
        'colaborador', 'usuario'
    ]
    with app.app_context():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                conn.commit()
    yield


@pytest.fixture()
def client(app, db):
    """Cliente HTTP de teste com contexto ativo."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture()
def auth_headers(client):
    """Cria usuário único e retorna headers com JWT válido."""
    unique = uuid.uuid4().hex[:8]
    username = f"testuser_{unique}"
    email = f"{username}@test.com"
    password = "Test@12345"

    response = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert response.status_code == 201, f"Falha no registro: {response.get_json()}"

    response = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    assert response.status_code == 200
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def colaborador_id(client, auth_headers):
    """Cria colaborador de teste e retorna seu ID."""
    response = client.post(
        "/api/colaboradores",
        headers=auth_headers,
        json={"nome": "Colaborador Teste", "dia_fechamento": 5},
    )
    assert response.status_code == 201
    return response.get_json()["id"]


@pytest.fixture()
def mes_vigente():
    """Retorna mês vigente no formato YYYY-MM."""
    return date.today().strftime("%Y-%m")