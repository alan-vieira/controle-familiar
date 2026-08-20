"""Testes completos do CRUD de rendas.
Cobre: upsert, atualizacao, remocao, filtros.
"""


class TestListagemRendas:
    """GET /api/rendas"""

    def test_listar_todas_rendas(self, client, auth_headers, colaborador_id):
        response = client.get("/api/rendas", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

    def test_listar_com_filtro_mes(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        # Cria renda no mes vigente
        client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "5000.00",
            },
        )

        response = client.get(
            f"/api/rendas?mes={mes_vigente}", headers=auth_headers
        )
        data = response.get_json()
        assert all(r["mes_ano"] == mes_vigente for r in data)

    def test_listar_sem_auth_retorna_401(self, client):
        """Lista rendas exige autenticacao."""
        response = client.get("/api/rendas")
        assert response.status_code == 401

    def test_listar_mes_invalido_retorna_400(self, client, auth_headers):
        response = client.get(
            "/api/rendas?mes=2026-13", headers=auth_headers
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_MONTH"


class TestUpsertRenda:
    """POST /api/rendas — cria ou atualiza (upsert)"""

    def test_criar_renda_nova(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert "id" in data
        assert data["message"] == "Renda registrada/atualizada com sucesso"

        # Verifica se foi criada via GET
        response = client.get(
            f"/api/rendas?mes={mes_vigente}", headers=auth_headers
        )
        rendas = response.get_json()
        created = next(r for r in rendas if r["id"] == data["id"])
        assert created["valor"] == "3000.00"

    def test_upsert_atualiza_renda_existente(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        # Cria renda inicial
        resp = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        assert resp.status_code in (200, 201)

        # Upsert com valor diferente (mesmo colaborador + mes)
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "4000.00",
            },
        )
        assert response.status_code in (200, 201)
        data = response.get_json()
        assert data["message"] == "Renda registrada/atualizada com sucesso"

        # Verifica se foi atualizado via GET
        response = client.get(
            f"/api/rendas?mes={mes_vigente}", headers=auth_headers
        )
        rendas = response.get_json()
        updated = next(r for r in rendas if r["colaborador_id"] == colaborador_id and r["mes_ano"] == mes_vigente)
        assert updated["valor"] == "4000.00"

    def test_upsert_colaborador_inexistente_retorna_404(
        self, client, auth_headers, mes_vigente
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": 999999,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        assert response.status_code == 404
        assert response.get_json()["code"] == "COLLABORATOR_NOT_FOUND"

    def test_upsert_mes_invalido_retorna_400(
        self, client, auth_headers, colaborador_id
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": "2026-13",
                "valor": "3000.00",
            },
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_FAILED"

    def test_upsert_valor_zero_rejeitado(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "0.00",
            },
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_FAILED"


class TestAtualizacaoRenda:
    """PUT /api/rendas/<id>"""

    def test_atualizar_renda(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        # Cria renda
        resp = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        renda_id = resp.get_json()["id"]

        # Atualiza
        response = client.put(
            f"/api/rendas/{renda_id}",
            headers=auth_headers,
            json={"valor": "3500.00"},
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Renda atualizada com sucesso"

        # Verifica se foi atualizado
        response = client.get(
            f"/api/rendas?mes={mes_vigente}", headers=auth_headers
        )
        rendas = response.get_json()
        updated = next(r for r in rendas if r["id"] == renda_id)
        assert updated["valor"] == "3500.00"

    def test_atualizar_renda_inexistente_retorna_404(
        self, client, auth_headers
    ):
        response = client.put(
            "/api/rendas/999999",
            headers=auth_headers,
            json={"valor": "1000.00"},
        )
        assert response.status_code == 404

    def test_atualizar_renda_valor_zero_rejeitado(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        resp = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        renda_id = resp.get_json()["id"]

        response = client.put(
            f"/api/rendas/{renda_id}",
            headers=auth_headers,
            json={"valor": "0.00"},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_VALUE"

    def test_atualizar_renda_valor_invalido_rejeitado(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        resp = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "3000.00",
            },
        )
        renda_id = resp.get_json()["id"]

        response = client.put(
            f"/api/rendas/{renda_id}",
            headers=auth_headers,
            json={"valor": "abc"},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_VALUE"


class TestRemocaoRenda:
    """DELETE /api/rendas/<id>"""

    def test_deletar_renda(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        resp = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "2000.00",
            },
        )
        renda_id = resp.get_json()["id"]

        response = client.delete(
            f"/api/rendas/{renda_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Renda deletada com sucesso"

        # Verifica que foi removida
        response = client.get(
            f"/api/rendas?mes={mes_vigente}", headers=auth_headers
        )
        ids = [r["id"] for r in response.get_json()]
        assert renda_id not in ids

    def test_deletar_renda_inexistente_retorna_404(
        self, client, auth_headers
    ):
        response = client.delete(
            "/api/rendas/999999", headers=auth_headers
        )
        assert response.status_code == 404


class TestValidacoesRenda:
    """Validacoes de entrada."""

    def test_valor_negativo_rejeitado(
        self, client, auth_headers, colaborador_id, mes_vigente
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "-100.00",
            },
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_FAILED"

    def test_mes_invalido_rejeitado(
        self, client, auth_headers, colaborador_id
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": "2026-13",  # invalido
                "valor": "1000.00",
            },
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_FAILED"

    def test_campos_obrigatorios_faltando(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/rendas",
            headers=auth_headers,
            json={},  # todos faltando
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_FAILED"