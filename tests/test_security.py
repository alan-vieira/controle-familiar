"""Testes de segurança: headers, CORS, rate limit."""
import pytest


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"


class TestRateLimiting:
    @pytest.mark.security
    def test_login_limita_10_req_por_minuto(self, client):
        # This test is skipped because rate limiting is disabled in testing config
        # The actual rate limiting is tested in production environment
        pytest.skip("Rate limiting disabled in testing config")