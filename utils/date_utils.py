# utils/date_utils.py
from datetime import date

def calcular_mes_vigente(data_compra: date, tipo_pg: str, dia_fechamento: int) -> str:
    """
    Calcula o mês vigente com base na data de compra, tipo de pagamento e dia de fechamento.
    
    Regras:
    - Débito, Pix, dinheiro: mes_vigente = mês da compra.
    - Crédito:
        - Se data_compra.day < dia_fechamento → mes_vigente = mês seguinte (M+1)
        - Se data_compra.day >= dia_fechamento → mes_vigente = mês + 2 (M+2)
    """
    tipo_pg_normalizado = tipo_pg.lower().strip()
    if tipo_pg_normalizado not in ('credito', 'cartao', 'cartão'):
        # Pagamento imediato
        return data_compra.strftime('%Y-%m')
    
    # Cartão de crédito → vai para o futuro
    if data_compra.day >= dia_fechamento:
        # Mês + 2
        year = data_compra.year
        month = data_compra.month + 2
        if month > 12:
            month -= 12
            year += 1
        return f"{year}-{month:02d}"
    else:
        # Mês + 1
        year = data_compra.year
        month = data_compra.month + 1
        if month > 12:
            month = 1
            year += 1
        return f"{year}-{month:02d}"
