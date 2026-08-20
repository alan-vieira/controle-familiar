"""Testes de precisão Decimal (regressão v0.2.0)."""
import json
from decimal import Decimal, ROUND_HALF_UP
from utils.json_utils import DecimalEncoder


class TestDecimalEncoder:
    def test_decimal_vira_string_no_json(self):
        valor = Decimal("1234.56")
        result = json.dumps({"valor": valor}, cls=DecimalEncoder)
        assert '"valor": "1234.56"' in result

    def test_decimal_com_muitas_casas_decimais(self):
        valor = Decimal("0.1") + Decimal("0.2")
        result = json.dumps({"soma": valor}, cls=DecimalEncoder)
        assert "0.30000000000000004" not in result
        assert '"soma": "0.3"' in result

    def test_soma_de_multiplos_valores_sem_drift(self):
        valores = [Decimal("0.10")] * 10
        total = sum(valores)
        assert total == Decimal("1.00")
        assert str(total) == "1.00"


class TestDivisaoProporcional:
    def test_divisao_por_tres_com_resto(self):
        total = Decimal("100.00")
        partes = 3
        valor_base = (total / partes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        resto = total - (valor_base * partes)
        assert resto == Decimal("0.01")