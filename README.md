# Controle Financeiro Familiar — API (Backend)

[![Tests & Coverage](https://github.com/alan-vieira/controle-familiar/actions/workflows/tests.yml/badge.svg)](https://github.com/alan-vieira/controle-familiar/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen)](https://github.com/alan-vieira/controle-familiar/actions)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render)](https://controle-familiar.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-black?logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791?logo=postgresql)](https://postgresql.org)
[![Release](https://img.shields.io/badge/Release-v0.4.0-orange)](https://github.com/alan-vieira/controle-familiar/releases/tag/v0.4.0)

API RESTful feita em **Python + Flask** para o projeto **Controle Financeiro Familiar**.
Gerencia colaboradores, rendas, despesas e o cálculo do resumo mensal, com autenticação JWT stateless e integração ao banco de dados **PostgreSQL** (Supabase/Render).

> 🌐 **URL de produção**: https://controle-familiar.onrender.com
> 📊 **Frontend**: https://github.com/alan-vieira/controle-familiar-frontend
> 🎯 **Projeto completo**: Sistema para gestão colaborativa de finanças domésticas

---

## 📦 Funcionalidades

- Autenticação de usuários (registro, login/logout/refresh com JWT)
- CRUD de:
  - **Colaboradores** (membros da família)
  - **Despesas** (com data, descrição, valor, categoria, tipo de pagamento e colaborador)
  - **Rendas mensais** (por colaborador)
  - **Divisão mensal** (status de acerto)
- Cálculo do **resumo financeiro mensal** (total de rendas, despesas e saldo por colaborador)
- Formatação de valores em **BRL** (R$) na apresentação com precisão decimal garantida

---

## 🗃️ Banco de Dados

- Hospedado no **Supabase** (PostgreSQL) ou **Render PostgreSQL**
- Acesso feito via **connection string PostgreSQL** (`DATABASE_URL`) usando `psycopg2`
- Pool de conexões thread-safe (`ThreadedConnectionPool`) para produção
- Tabelas principais:
  - `usuario` — autenticação
  - `colaborador` — membros da família
  - `despesa` — lançamentos de despesas
  - `renda_mensal` — rendas por colaborador/mês
  - `divisao_mensal` — status de acerto mensal
  - `token_blacklist` — revogação de tokens JWT (funciona multi-worker)

> ⚠️ O frontend **nunca acessa o banco diretamente**. Toda comunicação passa por esta API.

---

## 🛠️ Stack de Tecnologias

| Componente | Versão | Observação |
|---|---|---|
| **Python** | 3.10+ | Obrigatório |
| **Flask** | 3.1+ | Factory pattern, WSGI entry point |
| **PostgreSQL Driver** | psycopg2-binary 2.9+ | Pool thread-safe |
| **Auth** | Flask-JWT-Extended 4.7+ | Stateless JWT, refresh tokens |
| **Rate Limiting** | Flask-Limiter 4.1+ | Memória (free tier) / Redis opcional |
| **CORS** | flask-cors 6.0+ | Origens via variável de ambiente |
| **Security** | Werkzeug 3.1+ | PBKDF2 password hashing |
| **Deploy** | gunicorn 26+ | `--preload --timeout 60` |
| **Config** | python-dotenv 1.2+ | Fail-fast validation |

---

## ⚙️ Variáveis de Ambiente

Todas as variáveis são **obrigatórias** (fail-fast no startup). Não há fallbacks inseguros.

| Variável | Descrição | Exemplo / Default |
|---|---|---|
| `DATABASE_URL` | Connection string PostgreSQL completa | `postgresql://user:***@host:5432/db?sslmode=require` |
| `SECRET_KEY` | Chave secreta Flask (≥32 chars em produção) | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `JWT_SECRET_KEY` | Chave separada para assinar JWTs (≥32 chars) | Diferente da `SECRET_KEY` |
| `CORS_ORIGINS` | Origens permitidas (CSV, sem barra final) | `https://app.vercel.app,http://localhost:5173` |
| `FLASK_ENV` | Ambiente: `development`, `production`, `testing` | `production` |
| `JWT_ACCESS_TOKEN_EXPIRES_HOURS` | Expiração do access token | `1` (default) |
| `DATABASE_POOL_MAX` | Máximo de conexões no pool | `10` (default) |
| `DATABASE_SSLMODE` | Modo SSL do PostgreSQL | `require` (default) |

> 🔑 **Gere chaves fortes**: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
> ⚠️ `CORS_ORIGINS` deve incluir **todas** as origens do frontend (produção + desenvolvimento local).

---

## 🚀 Rodando Localmente

### 1. Clone o repositório

```bash
git clone https://github.com/alan-vieira/controle-familiar.git
cd controle-familiar
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate      # Linux / macOS / WSL
# venv\Scripts\activate       # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
# ou com uv (mais rápido)
uv pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais (veja a tabela de variáveis acima).

### 5. Execute a API

```bash
# Desenvolvimento (com hot reload)
flask run

# Ou diretamente com Python
python app.py
```

Acesse: http://localhost:5000

**Endpoints de saúde:**
- `GET /` — Status básico + versão
- `GET /health` — Health check detalhado (inclui `SELECT 1` no banco)

---

## 🌐 Endpoints da API

**Base path**: `/api`  
**Autenticação**: Header `Authorization: Bearer <access_token>` (JWT)

### Autenticação (`/api/auth`)

| Método | Rota | Descrição | Auth | Rate Limit |
|---|---|---|---|---|
| POST | `/api/auth/register` | Criar conta (username, email opcional, senha forte) | ❌ | 10/min |
| POST | `/api/auth/login` | Login (retorna access_token) | ❌ | 10/min |
| GET | `/api/auth/status` | Verificar sessão / token válido | ✅ | — |
| POST | `/api/auth/logout` | Revogar token (adiciona à blacklist) | ✅ | — |
| POST | `/api/auth/refresh` | Renovar access token via refresh token | ✅ (refresh) | — |

### Colaboradores (`/api/colaboradores`)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/api/colaboradores` | Listar todos | ✅ |
| POST | `/api/colaboradores` | Criar novo (nome, dia_fechamento 1–31) | ✅ |
| PUT | `/api/colaboradores/<id>` | Atualizar nome e dia_fechamento | ✅ |
| DELETE | `/api/colaboradores/<id>` | Remover (bloqueia se houver despesas/rendas) | ✅ |

### Despesas (`/api/despesas`)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/api/despesas` | Listar (filtro opcional `?mes_vigente=YYYY-MM`) | ✅ |
| POST | `/api/despesas` | Criar (data_compra, descricao, valor, tipo_pg, colaborador_id, categoria) | ✅ |
| PUT | `/api/despesas/<id>` | Atualizar | ✅ |
| DELETE | `/api/despesas/<id>` | Remover | ✅ |

> **Categorias válidas**: `moradia`, `alimentacao`, `restaurante_lanche`, `casa_utilidades`, `saude`, `transporte`, `lazer_outros`  
> **Tipos de pagamento**: `credito`, `debito`, `pix`, `dinheiro`, `outros`  
> **Validação**: `data_compra` não pode ser futura; `valor > 0`

### Rendas (`/api/rendas`)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/api/rendas` | Listar (filtro opcional `?mes=YYYY-MM`) | ✅ |
| POST | `/api/rendas` | Criar/atualizar (colaborador_id, mes_ano, valor) — upsert | ✅ |
| PUT | `/api/rendas/<id>` | Atualizar valor | ✅ |
| DELETE | `/api/rendas/<id>` | Remover | ✅ |

### Resumo Financeiro (`/api/resumo`)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/api/resumo/<YYYY-MM>` | Resumo do mês: totais, divisão proporcional, saldos por colaborador | ✅ |

### Divisão Mensal (`/api/divisao`)

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `/api/divisao/<YYYY-MM>` | Status da divisão (paga, data_acerto) | ✅ |
| POST | `/api/divisao/<YYYY-MM>/marcar-pago` | Marcar como paga (body opcional: `data_acerto`) | ✅ |
| POST | `/api/divisao/<YYYY-MM>/desmarcar-pago` | Desmarcar como paga | ✅ |

---

## 🔒 Segurança

| Camada | Implementação |
|---|---|
| **Autenticação** | JWT stateless (access + refresh tokens) via `flask-jwt-extended` |
| **Senhas** | Hash PBKDF2 via `werkzeug.security.generate_password_hash` / `check_password_hash` |
| **Rate Limiting** | 10 req/min em `/auth/register` e `/auth/login` (Flask-Limiter) |
| **Token Revocation** | Tabela `token_blacklist` no PostgreSQL (funciona multi-worker) |
| **CORS** | Restritivo — apenas origens em `CORS_ORIGINS` (CSV via env) |
| **Headers HTTP** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` (produção) |
| **Validação de Entrada** | Email, username, datas futuras, enums, integridade referencial (FK) |
| **Dependências** | CVEs corrigidos: Werkzeug ≥3.1.6, gunicorn ≥23.0, Flask-CORS ≥5.0 |

---

## 🧪 Testes Automatizados

O projeto possui uma suite robusta de testes automatizados (**156 testes**) com cobertura de código superior a **85%**, garantida por um pipeline de CI/CD no GitHub Actions que bloqueia merges que reduzam a qualidade.

### Rodando os Testes Localmente

A maneira mais fácil e segura de rodar os testes é usando o `Makefile` e o Docker (que sobe um banco PostgreSQL 15.6 isolado, idêntico ao de produção, sem poluir seu ambiente de desenvolvimento):

```bash
# 1. Subir o banco de dados de teste e rodar as migrations
make test-setup

# 2. Rodar todos os testes com relatório de cobertura no terminal e HTML
make test-cov

# 3. (Opcional) Derrubar o banco de teste após finalizar
make test-teardown
```

Ou, para rodar tudo em um único comando (setup + testes + teardown):

```bash
./scripts/run-tests.ps1  # Windows (PowerShell)
# ou
./scripts/run-tests.sh   # Linux / macOS / Git Bash
```

📊 **Relatório de Cobertura**: Após rodar `make test-cov`, abra o arquivo `htmlcov/index.html` no seu navegador para ver exatamente quais linhas de código estão cobertas pelos testes.

---

## 🌐 Deploy no Render

### 1. Vincule este repositório ao seu Render Dashboard

### 2. Escolha **Web Service**

### 3. Build Command

```bash
pip install -r requirements.txt
```

### 4. Start Command

```bash
gunicorn app:application --workers 2 --threads 4 --timeout 60 --preload
```

> **Importante**: O entry point WSGI é `app:application` (instância única criada no module load).  
> **Não use `eventlet`** — o app é síncrono, thread-safe via pool de conexões.  
> `--preload` carrega o app uma vez no master worker (economiza memória, evita pool duplicado).  
> `--timeout 60` evita kill prematuro em cold starts / queries lentas.

### 5. Variáveis de Ambiente no Render

Adicione **todas** as variáveis do `.env` no painel (Environment > Environment Variables):

- `FLASK_ENV=production`
- `SECRET_KEY` (gere uma nova para produção)
- `JWT_SECRET_KEY` (gere uma nova para produção)
- `JWT_ACCESS_TOKEN_EXPIRES_HOURS=1`
- `DATABASE_URL` (connection string do Render PostgreSQL ou Supabase)
- `DATABASE_SSLMODE=require`
- `DATABASE_POOL_MAX=10`
- `CORS_ORIGINS=https://controle-familiar-frontend.vercel.app` (adicione outras se necessário)

> ⚠️ **Cold start no Render Free Tier**: A primeira requisição após inatividade pode levar **30–60 segundos**. O frontend deve tratar isso com loading/retry.

---

## 🗄️ Migrações SQL (Executar Manualmente no Supabase/Render)

Após deploy, execute estes scripts **em ordem** no SQL Editor do Supabase ou via `psql`:

```sql
-- 1. Índices de performance (melhora queries de resumo e listagens)
\i migrations/001_add_indexes.sql

-- 2. Tabela de blacklist de tokens (necessária para logout funcionar multi-worker)
\i migrations/002_token_blacklist.sql
```

| Arquivo | Descrição |
|---|---|
| `migrations/001_add_indexes.sql` | Índices compostos em `despesa(colaborador_id, mes_vigente)`, `despesa(mes_vigente)`, `renda_mensal(mes_ano)`, `renda_mensal(colaborador_id, mes_ano)` |
| `migrations/002_token_blacklist.sql` | Tabela `token_blacklist(jti PK, revoked_at, expires_at)` + índice em `expires_at` para purga automática |

---

## 📄 Licença

Projeto pessoal — uso educacional e doméstico.
Sem licença aberta definida (todos os direitos reservados por enquanto).

---

## 🙋 Autor

Alan Silva Vieira

- GitHub: [@alan-vieira](https://github.com/alan-vieira)
- Projeto: Controle Financeiro Familiar