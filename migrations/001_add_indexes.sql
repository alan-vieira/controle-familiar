-- Migration 001: Add indexes for query optimization
-- Run this migration after deploying Fase 3 changes

-- Índices para otimizar queries frequentes

-- Otimiza busca de despesas por mês vigente (usado em resumo.py, despesas.py GET)
CREATE INDEX IF NOT EXISTS idx_despesa_mes_vigente 
ON despesa(mes_vigente);

-- Otimiza busca de despesas por colaborador e mês (usado em resumo.py - N+1 fix)
CREATE INDEX IF NOT EXISTS idx_despesa_colaborador_mes 
ON despesa(colaborador_id, mes_vigente);

-- Otimiza busca de rendas por mês (usado em resumo.py, rendas.py GET)
CREATE INDEX IF NOT EXISTS idx_renda_mes_ano 
ON renda_mensal(mes_ano);

-- Otimiza busca de rendas por colaborador e mês (usado em rendas.py)
CREATE INDEX IF NOT EXISTS idx_renda_colaborador_mes 
ON renda_mensal(colaborador_id, mes_ano);

-- Índices adicionais para performance geral (pode já existirem do schema.sql)
-- CREATE INDEX IF NOT EXISTS idx_despesa_colaborador ON despesa(colaborador_id);
-- CREATE INDEX IF NOT EXISTS idx_despesa_categoria ON despesa(categoria);
-- CREATE INDEX IF NOT EXISTS idx_renda_mes_ano ON renda_mensal(mes_ano);