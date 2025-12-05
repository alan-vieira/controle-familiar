from datetime import date, timedelta

def calcular_mes_vigente(data_compra: date, tipo_pg: str, dia_fechamento: int) -> str:
    """
    Calcula o mês vigente (mês da fatura) para cartões de crédito.
    
    Regra real:
    - O ciclo do cartão termina no dia `dia_fechamento` do mês seguinte à compra.
    - Se a compra ocorre ATÉ o dia de fechamento do ciclo atual → mês vigente = mês seguinte (M+1)
    - Se a compra ocorre APÓS esse dia → mês vigente = M+2
    """
    tipo_pg_normalizado = tipo_pg.lower().strip()
    
    # Normaliza tipos de crédito
    if tipo_pg_normalizado not in ('credito', 'crédito', 'cartao de credito', 'cartão de crédito', 'cartão', 'cartao'):
        # Pagamento imediato
        return data_compra.strftime('%Y-%m')

    # Determina o último dia do ciclo atual (dia_fechamento do próximo mês)
    # Ex: compra em nov/2025 → ciclo termina em 02/dez/2025
    if data_compra.month == 12:
        ciclo_fim = date(data_compra.year + 1, 1, dia_fechamento)
    else:
        ciclo_fim = date(data_compra.year, data_compra.month + 1, dia_fechamento)

    # Ajusta se o dia_fechamento for inválido (ex: 31 em mês com 30 dias)
    # (opcional: você pode adicionar validação aqui)

    if data_compra <= ciclo_fim:
        meses_a_adicionar = 1
    else:
        meses_a_adicionar = 2

    # Cálculo robusto do mês/ano
    total_months = data_compra.year * 12 + data_compra.month - 1 + meses_a_adicionar
    year = total_months // 12
    month = total_months % 12 + 1
    return f"{year}-{month:02d}"
