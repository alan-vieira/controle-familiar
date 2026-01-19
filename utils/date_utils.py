from datetime import date

def calcular_mes_vigente(data_compra: date, tipo_pg: str, dia_limite: int) -> str:
    """
    Calcula o mês de competência (mês vigente) com base na regra por colaborador:
    
    - Se a compra ocorre ATÉ o `dia_limite` → registra no MESMO mês da compra.
    - Se ocorre APÓS o `dia_limite` → registra no MÊS SEGUINTE.
    
    Parâmetros:
        data_compra (date): data da compra
        tipo_pg (str): tipo de pagamento (ex: 'cartão', 'crédito', etc.)
        dia_limite (int): dia limite do colaborador (ex: 2 para A, 8 para S)
    
    Retorna:
        str: mês vigente no formato 'YYYY-MM'
    """
    # Normaliza tipo de pagamento
    tipo_pg_normalizado = tipo_pg.lower().strip()
    
    # Se NÃO for cartão de crédito (ou similares), usa o próprio mês da compra
    if tipo_pg_normalizado not in ('credito', 'crédito', 'cartao de credito', 'cartão de crédito', 'cartão', 'cartao'):
        return data_compra.strftime('%Y-%m')

    # Aplica a regra personalizada por colaborador
    if data_compra.day <= dia_limite:
        return data_compra.strftime('%Y-%m')  # mesmo mês
    else:
        # Próximo mês (com rotação de ano)
        if data_compra.month == 12:
            return f"{data_compra.year + 1}-01"
        else:
            return f"{data_compra.year}-{data_compra.month + 1:02d}"
