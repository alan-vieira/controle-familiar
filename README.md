# Controle Financeiro Familiar — API (Backend)

[![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render)](https://controle-familiar.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791?logo=postgresql)](https://postgresql.org)

API RESTful feita em **Python + Flask** para o projeto **Controle Financeiro Familiar**.
Gerencia colaboradores, rendas, despesas, categorias e o cálculo do resumo mensal, com autenticação JWT e integração ao banco de dados **PostgreSQL** (Supabase/Render).

> 🌐 **URL de produção**: https://controle-familiar.onrender.com
> 📊 **Frontend**: https://github.com/alan-vieira/controle-familiar-frontend
> 🎯 **Projeto completo**: Sistema para gestão colaborativa de finanças domésticas

---

## 📦 Funcionalidades

- Autenticação de usuários (registro, login/logout com JWT)
- CRUD de:
  - **Colaboradores**
  - **Categorias de despesa** (extensível)
  - **Despesas** (com data, descrição, valor, categoria, tipo de pagamento e colaborador)
  - **Rendas mensais** (por colaborador)
  - **Configuração de fechamento mensal** (dia do mês)
  - **Divisão mensal** (status de acerto)
- Cálculo do **resumo financeiro mensal** (total de rendas, despesas e saldo por colaborador)
- Formatação de valores em **BRL** (R$) na apresentação

---

## 🗃️ Banco de Dados

- Hospedado no **Supabase** (PostgreSQL) ou **Render PostgreSQL**
- Acesso feito via **connection string PostgreSQL** (`DATABASE_URL`) usando `psycopg2`
- Pool de conexões thread-safe (`ThreadedConnectionPool`) para produção
- Tabelas principais:
  - `usuario` — autenticação
  - `colaborador` — membros da família
  - `categoria` — categorias de despesa (extensível)
  - `despesa` — lançamentos de despesas
  - `renda_mensal` — rendas por colaborador/mês
  - `divisao_mensal` — status de acerto mensal
  - `configuracao_fechamento` — dia de fechamento do mês

> ⚠️ O frontend **nunca acessa o banco diretamente**. Toda comunicação passa por esta API.

---

## 🛠️ Pré-requisitos

- Python 3.10+
- `pip` ou `uv`
- Conta no [Supabase](https://supabase.com) ou [Render](https://render.com) com PostgreSQL ativo
- (Opcional) [Docker](https://docker.com) para containerização

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

Copie o arquivo de exemplo e preencha com seus valores:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```ini
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=sua_chave_secreta_muito_forte_com_pelo_menos_32_caracteres
JWT_SECRET_KEY=outra_chave_forte_diferente_da_secret_key

# JWT Configuration
JWT_ACCESS_TOKEN_EXPIRES_HOURS=1

# Database Configuration
# Formato: postgresql://usuario:senha@host:porta/nome_do_banco?sslmode=require
DATABASE_URL=postgresql://usuario:senha@db.supabase.co:5432/postgres?sslmode=require
DATABASE_SSLMODE=require
DATABASE_POOL_MAX=10

# CORS Configuration
# Origens separadas por vírgula, SEM barra final
# Exemplo produção + desenvolvimento:
CORS_ORIGINS=https://controle-familiar-frontend.vercel.app,http://localhost:3000,http://127.0.0.1:5173
```

> 🔑 **Importante**:
> - `SECRET_KEY` e `JWT_SECRET_KEY` devem ser strings aleatórias longas (mín. 32 chars). Use `python -c "import secrets; print(secrets.token_urlsafe(32))"` para gerar.
> - `DATABASE_URL` deve ser a connection string completa do PostgreSQL (Supabase/Render).
> - `CORS_ORIGINS` deve incluir todas as origens do frontend (produção + desenvolvimento local).

### 5. Execute a API

```bash
# Desenvolvimento (com hot reload)
flask run

# Ou diretamente com Python
python app.py
```

Acesse: http://localhost:5000

Endpoints de saúde:
- `GET /` — Status básico
- `GET /health` — Health check detalhado (inclui conectividade com banco)

---

## 🌐 Endpoints da API (resumo)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| POST | `/api/auth/register` | Registra novo usuário |
| POST | `/api/login` | Autentica usuário (retorna JWT) |
| GET | `/api/auth/status` | Verifica status do token (requer JWT) |
| POST | `/api/logout` | Logout (cliente descarta token) |
| GET | `/api/colaboradores` | Lista colaboradores |
| POST | `/api/colaboradores` | Cria novo colaborador |
| PUT | `/api/colaboradores/<id>` | Atualiza colaborador |
| DELETE | `/api/colaboradores/<id>` | Remove colaborador |
| GET | `/api/despesas` | Lista despesas (filtro: `?mes_vigente=YYYY-MM`) |
| POST | `/api/despesas` | Registra nova despesa |
| PUT | `/api/despesas/<id>` | Atualiza despesa |
| DELETE | `/api/despesas/<id>` | Remove despesa |
| GET | `/api/rendas` | Lista rendas (filtro: `?mes=YYYY-MM`) |
| POST | `/api/rendas` | Registra/atualiza renda |
| PUT | `/api/rendas/<id>` | Atualiza valor da renda |
| DELETE | `/api/rendas/<id>` | Remove renda |
| GET | `/api/resumo/<mes_ano>` | Retorna resumo financeiro do mês |
| GET | `/api/divisao/<mes_ano>` | Status da divisão mensal |
| POST | `/api/divisao/<mes_ano>/marcar-pago` | Marca divisão como paga |
| POST | `/api/divisao/<mes_ano>/desmarcar-pago` | Desmarca divisão como paga |

> 🔒 **Todos os endpoints em `/api/*` exigem autenticação JWT** (header `Authorization: Bearer <token>`).

---

## 📤 Deploy no Render

### 1. Vincule este repositório ao seu Render Dashboard

### 2. Escolha **Web Service**

### 3. Build Command

```bash
pip install -r requirements.txt
```

### 4. Start Command

```bash
gunicorn app:application --workers 2 --threads 4 --timeout 30
```

> **Nota**: O entry point WSGI é `app:application` (instância única criada no module load).
> Não use `eventlet` a menos que tenha necessidade específica de WebSockets/async.

### 5. Variáveis de Ambiente no Render

Adicione **todas** as variáveis do `.env` no painel do Render (Environment > Environment Variables):

- `FLASK_ENV=production`
- `SECRET_KEY` (gere uma nova para produção)
- `JWT_SECRET_KEY` (gere uma nova para produção)
- `JWT_ACCESS_TOKEN_EXPIRES_HOURS=1`
- `DATABASE_URL` (connection string do Render PostgreSQL ou Supabase)
- `DATABASE_SSLMODE=require`
- `DATABASE_POOL_MAX=10`
- `CORS_ORIGINS=https://controle-familiar-frontend.vercel.app` (adicione outras se necessário)

> 💡 Render mantém o serviço ativo mesmo no plano gratuito, desde que receba requisições periódicas.

---

## 🔒 Segurança

- **JWT** para autenticação stateless (access tokens com expiração configurável)
- **Senhas** hasheadas com `werkzeug.security` (PBKDF2)
- **CORS** restritivo — apenas origens explicitamente permitidas via `CORS_ORIGINS`
- **Headers de segurança** — cookies seguros, HttpOnly, SameSite
- **Validação de entrada** em todas as rotas
- **Pool de conexões** com parâmetros seguros (sslmode=require)
- **Nenhum segredo no código** — tudo via variáveis de ambiente

---

## 🧪 Testes

```bash
# Configurar variáveis de teste
export FLASK_ENV=testing
export TEST_DATABASE_URL=postgresql://...

# Executar testes (quando implementados)
pytest tests/
```

---

## 📄 Licença

Projeto pessoal — uso educacional e doméstico.
Sem licença aberta definida (todos os direitos reservados por enquanto).

---

## 🙋 Autor

Alan Silva Vieira

- GitHub: [@alan-vieira](https://github.com/alan-vieira)
- Projeto: Controle Financeiro Familiar