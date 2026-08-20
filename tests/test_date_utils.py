"""
Testes de utilitários de data.
Cobre: cálculo de mês vigente, edge cases.
"""
from datetime import date
import pytest


class TestCalcularMesVigente:
    """Cálculo do mês vigente (competência)."""

    def test_mes_vigente_sem_cartao_retorna_mes_da_compra(self):
        """Se tipo_pg NÃO for cartão, retorna mês da compra."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 15), 
            "pix",  # não é cartão
            5
        )
        assert result == "2026-08"

    def test_mes_vigente_cartao_ate_dia_limite_mesmo_mes(self):
        """Cartão: compra até dia_limite → mesmo mês."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 5),  # dia 5
            "credito",
            5  # dia_limite = 5
        )
        assert result == "2026-08"

    def test_mes_vigente_cartao_apos_dia_limite_proximo_mes(self):
        """Cartão: compra após dia_limite → próximo mês."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 10),  # dia 10
            "credito",
            5  # dia_limite = 5
        )
        assert result == "2026-09"

    def test_mes_vigente_cartao_dezembro_vira_janeiro(self):
        """Cartão em dezembro após dia_limite → janeiro do ano seguinte."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 12, 20),
            "credito",
            15
        )
        assert result == "2027-01"

    def test_mes_vigente_cartao_variacoes_nome(self):
        """Variações de nome de cartão devem ser normalizadas."""
        from utils.date_utils import calcular_mes_vigente
        
        for tipo in ("credito", "crédito", "cartao de credito", "cartão de crédito", "cartão", "cartao"):
            result = calcular_mes_vigente(
                date(2026, 8, 20),
                tipo,
                10
            )
            assert result == "2026-09", f"Falhou para tipo: {tipo}"

    def test_mes_vigente_cartao_maiusculas(self):
        """Nomes com maiúsculas devem ser normalizados."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 20),
            "CREDITO",
            10
        )
        assert result == "2026-09"

    def test_mes_vigente_cartao_com_espacos(self):
        """Nomes com espaços extras devem ser normalizados."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 20),
            "  credito  ",
            10
        )
        assert result == "2026-09"

    def test_mes_vigente_debito_nao_aplica_regra(self):
        """Débito não aplica regra de dia_limite (é como pix)."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 20),
            "debito",
            5  # dia_limite ignorado
        )
        assert result == "2026-08"

    def test_mes_vigente_dinheiro_nao_aplica_regra(self):
        """Dinheiro não aplica regra de dia_limite."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 20),
            "dinheiro",
            5
        )
        assert result == "2026-08"

    def test_mes_vigente_outros_nao_aplica_regra(self):
        """Tipo 'outros' não aplica regra de dia_limite."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 20),
            "outros",
            5
        )
        assert result == "2026-08"

    def test_mes_vigente_dia_igual_limite_mesmo_mes(self):
        """Se dia_compra == dia_limite → mesmo mês."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 10),
            "credito",
            10
        )
        assert result == "2026-08"

    def test_mes_vigente_dia_um_apos_limite_proximo_mes(self):
        """Se dia_compra == dia_limite + 1 → próximo mês."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2026, 8, 11),
            "credito",
            10
        )
        assert result == "2026-09"

    def test_mes_vigente_jan_apos_dez(self):
        """Dezembro → Janeiro funciona corretamente."""
        from utils.date_utils import calcular_mes_vigente
        
        result = calcular_mes_vigente(
            date(2025, 12, 25),
            "credito",
            20
        )
        assert result == "2026-01"