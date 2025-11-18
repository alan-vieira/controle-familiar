from datetime import date

def calcular_mes_vigente(data_compra: date, tipo_pg: str, dia_fechamento: int) -> str:
    if tipo_pg.lower() not in ('credito', 'cartao'):
        return data_compra.strftime('%Y-%m')
    if data_compra.day <= dia_fechamento:
        return data_compra.strftime('%Y-%m')
    else:
        if data_compra.month == 12:
            return f"{data_compra.year + 1}-01"
        return f"{data_compra.year}-{data_compra.month + 1:02d}"
