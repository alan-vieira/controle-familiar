"""Testes do endpoint /api/divisao/<YYYY-MM>.
Cobre: listagem, marcar pago, desmarcar pago, validacoes.
"""
from datetime import date


class TestListagemDivisao:
    """GET /api/divisao/<YYYY-MM>"""

    def test_listagem_mes_sem_dados(self, client, auth_headers, mes_vigente):
        """Mes sem divisao deve retornar lista vazia."""
        response = client.get(
            f"/api/divisao/{mes_vigente}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data["mes_ano"] == mes_vigente
        assert data["paga"] is False
        assert data["data_acerto"] is None

    def test_listagem_mes_invalido_retorna_400(self, client, auth_headers):
        """Mes fora do formato YYYY-MM deve retornar 400."""
        response = client.get(
            "/api/divisao/2026-13", headers=auth_headers  # mes 13 invalido
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_MONTH"

    def test_listagem_sem_auth_retorna_401(self, client):
        """Endpoint protegido deve exigir autenticacao."""
        response = client.get("/api/divisao/2026-08")
        assert response.status_code == 401


class TestMarcarPago:
    """POST /api/divisao/<YYYY-MM>/marcar-pago"""

    def test_marcar_pago_com_data_acerto(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        """Marcar como paga com data_acerto especifica."""
        # Cria despesa para gerar divisao (mesmo que nao precise, endpoint funciona independentemente)
        client.post(
            "/api/despesas",
            headers=auth_headers,
            json={
                "data_compra": f"{mes_vigente}-10",
                "descricao": "Teste divisao",
                "valor": "100.00",
                "tipo_pg": "pix",
                "colaborador_id": colaborador_id,
                "categoria": "moradia",
            },
        )

        # Marca como paga
        response = client.post(
            f"/api/divisao/{mes_vigente}/marcar-pago",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "data_acerto": f"{mes_vigente}-20",
            },
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data["paga"] is True
        assert data["data_acerto"] == f"{mes_vigente}-20"

    def test_marcar_pago_sem_data_acerto(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        """data_acerto e opcional — deve usar null como default."""
        client.post(
            "/api/despesas",
            headers=auth_headers,
            json={
                "data_compra": f"{mes_vigente}-10",
                "descricao": "Teste sem data",
                "valor": "50.00",
                "tipo_pg": "pix",
                "colaborador_id": colaborador_id,
                "categoria": "alimentacao",
            },
        )

        response = client.post(
            f"/api/divisao/{mes_vigente}/marcar-pago",
            headers=auth_headers,
            json={"colaborador_id": colaborador_id},
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data["paga"] is True
        assert data["data_acerto"] is None


class TestDesmarcarPago:
    """POST /api/divisao/<YYYY-MM>/desmarcar-pago"""

    def test_desmarcar_pago(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        """Desmarcar uma divisao que estava paga."""
        # Cria despesa
        client.post(
            "/api/despesas",
            headers=auth_headers,
            json={
                "data_compra": f"{mes_vigente}-10",
                "descricao": "Teste desmarcar",
                "valor": "75.00",
                "tipo_pg": "pix",
                "colaborador_id": colaborador_id,
                "categoria": "lazer_outros",
            },
        )

        # Marca como paga
        client.post(
            f"/api/divisao/{mes_vigente}/marcar-pago",
            headers=auth_headers,
            json={"colaborador_id": colaborador_id},
        )

        # Desmarca
        response = client.post(
            f"/api/divisao/{mes_vigente}/desmarcar-pago",
            headers=auth_headers,
            json={"colaborador_id": colaborador_id},
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data["paga"] is False
        assert data["data_acerto"] is None

    def test_desmarcar_pago_cria_registro_se_inexistente(
        self, client, auth_headers, mes_vigente
    ):
        """Desmarcar cria registro se nao existir (upsert com paga=false)."""
        response = client.post(
            f"/api/divisao/{mes_vigente}/desmarcar-pago",
            headers=auth_headers,
            json={"colaborador_id": 1},
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data["paga"] is False
        assert data["data_acerto"] is None


class TestValidacoesDivisao:
    """Validacoes de entrada."""

    def test_marcar_pago_mes_invalido_retorna_400(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/divisao/2026-13/marcar-pago",
            headers=auth_headers,
            json={"colaborador_id": 1},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_MONTH"

    def test_marcar_pago_data_acerto_invalida(
        self, client, auth_headers, mes_vigente
    ):
        response = client.post(
            f"/api/divisao/{mes_vigente}/marcar-pago",
            headers=auth_headers,
            json={"colaborador_id": 1, "data_acerto": "data-invalida"},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_DATE"

    def test_desmarcar_pago_mes_invalido_retorna_400(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/divisao/2026-13/desmarcar-pago",
            headers=auth_headers,
            json={"colaborador_id": 1},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_MONTH"