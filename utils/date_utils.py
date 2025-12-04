# utils/date_utils.py
def calcular_mes_vigente(data_compra: date, tipo_pg: str, dia_fechamento: int) -> str:
    """
    Calcula o mês vigente com base na data de compra, tipo de pagamento e dia de fechamento.
    
    Regras:
    - Débito, Pix, dinheiro: mes_vigente = mês da compra.
    - Cartão de crédito:
        - A fatura é do mês seguinte ao mês em que o fechamento ocorre.
        - Ex: fechamento em 10/04 → fatura de abril → mes_vigente = "2025-04"
        - Compras entre 11/03 e 10/04 → mes_vigente = "2025-04"
    """
    tipo_pg_normalizado = tipo_pg.lower().strip()
    if tipo_pg_normalizado not in ('credito', 'cartao', 'cartão'):
        # Pagamento imediato → mês da compra
        return data_compra.strftime('%Y-%m')

    # --- Lógica para cartão de crédito ---
    # Constrói a data de fechamento no mesmo mês da compra
    try:
        fechamento_mes_compra = date(data_compra.year, data_compra.month, dia_fechamento)
    except ValueError:
        # Caso o dia_fechamento seja inválido para o mês (ex: 31 em fevereiro)
        # Usa o último dia do mês
        import calendar
        ultimo_dia = calendar.monthrange(data_compra.year, data_compra.month)[1]
        fechamento_mes_compra = date(data_compra.year, data_compra.month, ultimo_dia)

    if data_compra <= fechamento_mes_compra:
        # Compra entra na fatura do próprio mês → mes_vigente = mês da compra
        return data_compra.strftime('%Y-%m')
    else:
        # Compra entra na fatura do mês seguinte
        year = data_compra.year
        month = data_compra.month + 1
        if month > 12:
            month = 1
            year += 1
        return f"{year}-{month:02d}"
