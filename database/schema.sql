-- 1. Tabela de colaboradores
CREATE TABLE IF NOT EXISTS colaborador (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    dia_fechamento INTEGER NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31)
);

-- 2. Tabela de rendas mensais
CREATE TABLE IF NOT EXISTS renda_mensal (
    id SERIAL PRIMARY KEY,
    colaborador_id INTEGER NOT NULL REFERENCES colaborador(id) ON DELETE CASCADE,
    mes_ano VARCHAR(7) NOT NULL CHECK (mes_ano ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    valor DECIMAL(10,2) NOT NULL CHECK (valor >= 0),
    UNIQUE(colaborador_id, mes_ano)
);

-- 3. Tabela de despesas (ATUALIZADA com constraints)
CREATE TABLE IF NOT EXISTS despesa (
    id SERIAL PRIMARY KEY,
    data_compra DATE NOT NULL,
    mes_vigente VARCHAR(7) NOT NULL CHECK (mes_vigente ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    descricao TEXT NOT NULL,
    valor DECIMAL(10,2) NOT NULL CHECK (valor > 0),
    tipo_pg VARCHAR(20) NOT NULL CHECK (tipo_pg IN ('credito', 'debito', 'pix', 'dinheiro', 'outros')),
    colaborador_id INTEGER NOT NULL REFERENCES colaborador(id) ON DELETE CASCADE,
    categoria VARCHAR(30) NOT NULL CHECK (
        categoria IN (
            'moradia',
            'alimentacao',
            'restaurante_lanche',
            'casa_utilidades',
            'saude',
            'transporte',
            'lazer_outros'
        )
    )
);

-- 4. Tabela para divisão mensal
CREATE TABLE IF NOT EXISTS divisao_mensal (
    mes_ano VARCHAR(7) PRIMARY KEY,
    paga BOOLEAN NOT NULL DEFAULT false,
    data_acerto DATE,
    CHECK (mes_ano ~ '^\d{4}-(0[1-9]|1[0-2])$')
);

-- 5. Tabela de usuários (ATUALIZADA com campos completos)
CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT true
);

-- 6. Índices para desempenho
CREATE INDEX IF NOT EXISTS idx_despesa_mes_vigente ON despesa(mes_vigente);
CREATE INDEX IF NOT EXISTS idx_despesa_colaborador ON despesa(colaborador_id);
CREATE INDEX IF NOT EXISTS idx_despesa_categoria ON despesa(categoria);
CREATE INDEX IF NOT EXISTS idx_renda_mes_ano ON renda_mensal(mes_ano);
CREATE INDEX IF NOT EXISTS idx_usuario_username ON usuario(username);
CREATE INDEX IF NOT EXISTS idx_usuario_email ON usuario(email);


-- Ninguém pode mais acessar public.* via API REST (PostgREST).
-- 1. Revogar acesso de roles públicas (anon, authenticated) ao esquema public
REVOKE USAGE ON SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

-- 2. (Opcional) Garantir que novas tabelas futuras também não herdem permissões
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;