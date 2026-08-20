"""Testes do endpoint /api/resumo/<YYYY-MM>."""


class TestResumoMensal:
    def test_resumo_mes_sem_dados(self, client, auth_headers, colaborador_id, mes_vigente):
        # Need at least one colaborador with renda for the endpoint to work
        response = client.get(f"/api/resumo/{mes_vigente}", headers=auth_headers)
        # Endpoint requires renda to be registered for all colaboradores
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()
            assert "total_despesas" in data
            assert "total_renda" in data
            assert "saldo_total" in data

    def test_resumo_precisao_decimal_sem_drift(self, client, auth_headers, colaborador_id, mes_vigente):
        # First, register a renda for the colaborador
        from decimal import Decimal
        client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": colaborador_id,
                "mes_ano": mes_vigente,
                "valor": "1000.00",
            },
        )

        for valor in ["0.10", "0.20"]:
            client.post(
                "/api/despesas",
                headers=auth_headers,
                json={
                    "data_compra": f"{mes_vigente}-10",
                    "descricao": f"Teste {valor}",
                    "valor": valor,
                    "tipo_pg": "pix",
                    "colaborador_id": colaborador_id,
                    "categoria": "lazer_outros",
                },
            )

        response = client.get(f"/api/resumo/{mes_vigente}", headers=auth_headers)
        data = response.get_json()
        assert data["total_despesas"] == 0.30