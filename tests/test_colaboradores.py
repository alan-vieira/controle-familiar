"""Testes expandidos de colaboradores.
Adiciona: PUT, listagem detalhada, validacoes.
"""


class TestListagemColaboradores:
    """GET /api/colaboradores"""

    def test_listar_colaboradores_vazio(self, client, auth_headers):
        """Lista vazia quando nao ha colaboradores."""
        response = client.get("/api/colaboradores", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_listar_com_colaboradores(
        self, client, auth_headers, colaborador_id
    ):
        response = client.get("/api/colaboradores", headers=auth_headers)
        data = response.get_json()
        assert len(data) >= 1
        # Verifica campos esperados
        colab = data[0]
        assert "id" in colab
        assert "nome" in colab
        assert "dia_fechamento" in colab

    def test_listar_sem_auth_retorna_401(self, client):
        """Lista colaboradores exige autenticacao."""
        response = client.get("/api/colaboradores")
        assert response.status_code == 401


class TestAtualizacaoColaborador:
    """PUT /api/colaboradores/<id>"""

    def test_atualizar_nome(self, client, auth_headers, colaborador_id):
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Novo Nome", "dia_fechamento": 5},
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Colaborador atualizado com sucesso"

        # Verifica se foi atualizado
        response = client.get("/api/colaboradores", headers=auth_headers)
        data = response.get_json()
        updated = next(c for c in data if c["id"] == colaborador_id)
        assert updated["nome"] == "Novo Nome"

    def test_atualizar_dia_fechamento(
        self, client, auth_headers, colaborador_id
    ):
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Colaborador Teste", "dia_fechamento": 20},
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Colaborador atualizado com sucesso"

        # Verifica se foi atualizado
        response = client.get("/api/colaboradores", headers=auth_headers)
        data = response.get_json()
        updated = next(c for c in data if c["id"] == colaborador_id)
        assert updated["dia_fechamento"] == 20

    def test_atualizar_colaborador_inexistente_retorna_404(
        self, client, auth_headers
    ):
        response = client.put(
            "/api/colaboradores/999999",
            headers=auth_headers,
            json={"nome": "Teste", "dia_fechamento": 10},
        )
        assert response.status_code == 404

    def test_dia_fechamento_invalido_zero_rejeitado(
        self, client, auth_headers, colaborador_id
    ):
        # Dia 0 e invalido (deve ser 1-31)
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Teste", "dia_fechamento": 0},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_DAY"

    def test_dia_fechamento_invalido_32_rejeitado(
        self, client, auth_headers, colaborador_id
    ):
        # Dia 32 tambem e invalido
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Teste", "dia_fechamento": 32},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_DAY"

    def test_dia_fechamento_nao_numerico_rejeitado(
        self, client, auth_headers, colaborador_id
    ):
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Teste", "dia_fechamento": "abc"},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_DAY"

    def test_nome_vazio_rejeitado(
        self, client, auth_headers, colaborador_id
    ):
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "", "dia_fechamento": 10},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "MISSING_FIELDS"

    def test_campos_obrigatorios_faltando(
        self, client, auth_headers, colaborador_id
    ):
        response = client.put(
            f"/api/colaboradores/{colaborador_id}",
            headers=auth_headers,
            json={"nome": "Teste"},  # faltando dia_fechamento
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "MISSING_FIELDS"


class TestRemocaoColaborador:
    """DELETE /api/colaboradores/<id>"""

    def test_deletar_colaborador_sem_vinculos(
        self, client, auth_headers
    ):
        # Cria colaborador novo sem despesas/rendas
        resp = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "Para Deletar", "dia_fechamento": 15},
        )
        cid = resp.get_json()["id"]

        response = client.delete(
            f"/api/colaboradores/{cid}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Colaborador excluído com sucesso"

        # Verifica que foi removido
        response = client.get("/api/colaboradores", headers=auth_headers)
        ids = [c["id"] for c in response.get_json()]
        assert cid not in ids

    def test_deletar_colaborador_com_despesas_retorna_409(
        self, client, auth_headers
    ):
        # Cria colaborador
        resp = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "Com Despesa", "dia_fechamento": 5},
        )
        cid = resp.get_json()["id"]

        # Cria despesa vinculada
        client.post(
            "/api/despesas",
            headers=auth_headers,
            json={
                "data_compra": "2026-08-15",
                "descricao": "Mercado",
                "valor": "150.50",
                "tipo_pg": "pix",
                "colaborador_id": cid,
                "categoria": "alimentacao",
            },
        )

        response = client.delete(
            f"/api/colaboradores/{cid}", headers=auth_headers
        )
        assert response.status_code == 409
        assert response.get_json()["code"] == "HAS_EXPENSES"

    def test_deletar_colaborador_com_rendas_retorna_409(
        self, client, auth_headers, mes_vigente
    ):
        # Cria colaborador
        resp = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "Com Renda", "dia_fechamento": 10},
        )
        cid = resp.get_json()["id"]

        # Cria renda vinculada
        client.post(
            "/api/rendas",
            headers=auth_headers,
            json={
                "colaborador_id": cid,
                "mes_ano": mes_vigente,
                "valor": "5000.00",
            },
        )

        response = client.delete(
            f"/api/colaboradores/{cid}", headers=auth_headers
        )
        assert response.status_code == 409
        assert response.get_json()["code"] == "HAS_INCOMES"

    def test_deletar_colaborador_inexistente_retorna_404(
        self, client, auth_headers
    ):
        response = client.delete(
            "/api/colaboradores/999999", headers=auth_headers
        )
        assert response.status_code == 404


class TestValidacoesColaborador:
    """Validacoes de entrada adicionais."""

    def test_criar_colaborador_nome_vazio_rejeitado(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "", "dia_fechamento": 10},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "MISSING_FIELDS"

    def test_criar_colaborador_dia_invalido_rejeitado(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "Teste", "dia_fechamento": 0},
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_DAY"

    def test_criar_colaborador_campos_faltando(
        self, client, auth_headers
    ):
        response = client.post(
            "/api/colaboradores",
            headers=auth_headers,
            json={"nome": "Teste"},  # faltando dia_fechamento
        )
        assert response.status_code == 400
        assert response.get_json()["code"] == "MISSING_FIELDS"