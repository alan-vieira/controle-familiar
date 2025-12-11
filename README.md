# Controle Financeiro Familiar — API (Backend)

[![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render)](https://controle-familiar.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)](https://flask.palletsprojects.com)

API RESTful feita em **Python + Flask** para o projeto **Controle Financeiro Familiar**.  
Gerencia colaboradores, rendas, despesas, categorias e o cálculo do resumo mensal, com autenticação própria e integração ao banco de dados no **Supabase**.

> 🌐 **URL de produção**: https://controle-familiar.onrender.com  
> 📊 **Frontend**: https://github.com/alan-vieira/controle-familiar-frontend  
> 🎯 **Projeto completo**: Sistema para gestão colaborativa de finanças domésticas

---

## 📦 Funcionalidades

- Autenticação de usuários (login/logout com sessão segura)
- CRUD de:
  - **Colaboradores**
  - **Categorias de despesa**
  - **Despesas** (com data, descrição, valor, categoria e colaborador)
  - **Rendas mensais** (por colaborador)
  - **Configuração de fechamento mensal** (dia do mês)
- Cálculo do **resumo financeiro mensal** (total de rendas, despesas e saldo)
- Formatação de valores em **BRL** (R$) na apresentação (se aplicável)

---

## 🗃️ Banco de Dados

- Hospedado no **Supabase** (PostgreSQL)
- Acesso feito via **chave de serviço** (`SUPABASE_SERVICE_KEY`)
- Tabelas principais:
  - `colaborador`
  - `categoria`
  - `despesa`
  - `renda_mensal`
  - `configuracao_fechamento`

> ⚠️ O frontend **nunca acessa o Supabase diretamente**. Toda comunicação passa por esta API.

---

## 🛠️ Pré-requisitos

- Python 3.10+
- `pip`
- Conta no [Supabase](https://supabase.com) com projeto ativo
- (Opcional) [Render](https://render.com) para deploy

---

## 🚀 Rodando Localmente

1. **Clone o repositório**
   ```bash
   git clone https://github.com/alan-vieira/controle-familiar.git
   cd controle-familiar
   ```

2. **Crie e ative o ambiente virtual**
    ```bash
    python -m venv venv
    source venv/bin/activate      # Linux / macOS / WSL
    # venv\Scripts\activate       # Windows
    ```

3. **Instale as dependências**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure as variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto:

    SUPABASE_URL=https://<seu-projeto>.supabase.co
    SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
    SECRET_KEY=sua_chave_secreta_muito_forte_aqui
    FLASK_APP=app.py
    FLASK_ENV=development


🔑 A `SUPABASE_SERVICE_KEY` deve ser obtida nas Configurações > API do seu projeto no Supabase.
Nunca commite essa chave!

5. **Execute a API**

    ```bash
    flask run
    ```

Acesse: http://localhost:5000

## 🌐 Endpoints da API (resumo)

| Método | Caminho                     | Descrição                                |
|--------|-----------------------------|------------------------------------------|
| POST   | `/login`                    | Autentica usuário                        |
| POST   | `/logout`                   | Finaliza sessão                          |
| GET    | `/api/colaboradores`        | Lista colaboradores                      |
| POST   | `/api/colaboradores`        | Cria novo colaborador                    |
| GET    | `/api/despesas`             | Lista despesas                           |
| POST   | `/api/despesas`             | Registra nova despesa                    |
| GET    | `/api/rendas`               | Lista rendas mensais                     |
| POST   | `/api/rendas`               | Registra renda                           |
| GET    | `/api/resumo`               | Retorna resumo financeiro do mês atual   |
| GET    | `/api/configuracao`         | Dia de fechamento                        |
| PUT    | `/api/configuracao`         | Atualiza dia de fechamento               |

> 🔒 Todos os endpoints em `/api/*` exigem autenticação (sessão válida).

## 📤 Deploy no Render

1. Vincule este repositório ao seu Render Dashboard
2. Escolha Web Service
3. Build command (se necessário): (deixe vazio — Render detecta Flask automaticamente)
4. Start command:

    ```bash
    gunicorn --worker-class eventlet -k eventlet -w 1 app:app
    ```

ou, se usar apenas Flask:

    
    python app.py
    

5. Adicione as mesmas variáveis de ambiente do `.env` no painel do Render

> 💡 Render mantém o serviço ativo mesmo no plano gratuito, desde que receba requisições periódicas.

## 📄 Licença

Projeto pessoal — uso educacional e doméstico.
Sem licença aberta definida (todos os direitos reservados por enquanto).

## 🙋 Autor

Alan Silva Vieira

- GitHub: @alan-vieira
- Projeto: Controle Financeiro Familiar