# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- **Application Factory Pattern**: `create_app()` function em `app.py` para criação única da instância Flask
- **WSGI Entry Point**: Variável `application = create_app()` no module level para gunicorn
- **Configuração por Ambiente**: Classes `DevelopmentConfig`, `ProductionConfig`, `TestingConfig` em `config.py`
- **Validação de Configuração Obrigatória**: Inicialização falha se `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS` não estiverem definidas
- **Pool de Conexões PostgreSQL**: `ThreadedConnectionPool` em `connection.py` com `minconn=1`, `maxconn=DATABASE_POOL_MAX`
- **Context Managers Seguros**: `get_db_connection()` e `get_db_cursor()` com rollback automático e devolução ao pool
- **CORS Configurável via Ambiente**: `CORS_ORIGINS` aceita múltiplas origens separadas por vírgula
- **Método PATCH no CORS**: Suporte a `PATCH` além de `GET, POST, PUT, DELETE, OPTIONS`
- **Tratamento Global de Erros**: Handlers para `HTTPException` e `Exception` genérica com respostas JSON padronizadas
- **JWT Error Handlers**: Callbacks para token expirado, inválido, ausente, não renovado, revogado
- **Health Check Detalhado**: `/health` verifica conectividade com banco de dados
- **Schema de Banco Completo**: `init_db()` cria todas as tabelas necessárias (usuario, colaborador, categoria, despesa, renda_mensal, divisao_mensal, configuracao_fechamento)
- **Normalização de URL do Banco**: Conversão automática `postgres://` → `postgresql://`
- **Respeito ao sslmode da URL**: Não sobrescreve `sslmode` se já presente na `DATABASE_URL`
- **Arquivo `.env.example`**: Template com todas as variáveis necessárias
- **Logging Estruturado**: Configuração básica com formato timestamp + level + logger

### Changed
- **`app.py`**: Corrigido `Flask(name)` → `Flask(__name__)` e `if name == 'main':` → `if __name__ == '__main__':`
- **`app.py`**: Removido recriação da app a cada request no handler WSGI (era `def application(environ, start_response): app = create_app()`)
- **`app.py`**: Linha `Importe seus routes` transformada em imports reais dos blueprints
- **`app.py`**: CORS hardcoded removido → agora usa `CurrentConfig.CORS_ORIGINS` do ambiente
- **`config.py`**: Removido fallback inseguro `'sua_chave_secreta_aleatoria_segura'` para `SECRET_KEY`
- **`config.py`**: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS` agora são obrigatórios
- **`config.py`**: Adicionado `JWT_ACCESS_TOKEN_EXPIRES_HOURS`, `DATABASE_SSLMODE`, `DATABASE_POOL_MAX` configuráveis
- **`connection.py`**: Substituída conexão simples por `ThreadedConnectionPool`
- **`connection.py`**: `get_db_connection()` agora retorna context manager (usa `with`)
- **`connection.py`**: Adicionado `get_db_cursor()` para queries diretas com commit/rollback automático
- **`connection.py`**: `init_db()` expandido para criar todas as tabelas do schema
- **`README.md`**: Corrigida inconsistência `SUPABASE_SERVICE_KEY` → `DATABASE_URL` (connection string PostgreSQL)
- **`README.md`**: Atualizado comando de start no Render para `gunicorn app:application --workers 2 --threads 4 --timeout 30`
- **`README.md`**: Removida recomendação de `eventlet` (agora opcional, não padrão)
- **`README.md`**: Atualizado exemplo de `.env` com todas as variáveis documentadas
- **`README.md`**: Adicionada seção de Segurança e endpoints completos da API

### Fixed
- **Sintaxe**: `Flask(__name__)` e `if __name__ == '__main__':` corrigidos
- **Indentação**: Corrigidas indentação inconsistentes em `app.py`
- **WSGI**: Aplicação Flask criada uma única vez no module load (`application = create_app()`)
- **Segurança**: `SECRET_KEY` sem fallback inseguro — falha na inicialização se ausente
- **Segurança**: Validação de `SECRET_KEY` mínima de 32 chars em produção
- **Segurança**: `CORS_ORIGINS` obrigatório — sem origens permitidas por padrão
- **Conexão DB**: Pool de conexões evita exaustão de conexões em produção
- **Conexão DB**: Rollback automático em exceções dentro do context manager
- **Conexão DB**: Conexões devolvidas corretamente ao pool no `finally`
- **URL DB**: Normalização `postgres://` → `postgresql://` para compatibilidade psycopg2
- **SSL**: `sslmode` respeitado se já presente na `DATABASE_URL`

### Security
- **SECRET_KEY**: Não permite fallback inseguro; valida comprimento mínimo em produção
- **JWT_SECRET_KEY**: Separada da `SECRET_KEY`, obrigatória
- **CORS**: Origens restritivas via `CORS_ORIGINS` — sem wildcard
- **Cookies**: `Secure`, `HttpOnly`, `SameSite=Lax` em produção
- **Headers CORS**: `expose_headers` limitado, `max_age` para cache de preflight
- **Erros**: Detalhes de exceção não vazam em produção (apenas em `DEBUG=True`)

### Removed
- **`app.py`**: Handler WSGI legacy que recriava app por request
- **`config.py`**: Fallback inseguro para `SECRET_KEY`
- **`connection.py`**: `get_db_connection()` simples sem pool (mantido como `get_db_connection_legacy()` deprecated)
- **`README.md`**: Referência a `SUPABASE_SERVICE_KEY` (usava supabase-py, não psycopg2)
- **`README.md`**: Comando `gunicorn --worker-class eventlet` como padrão

---

## [0.1.0] - YYYY-MM-DD

### Added
- Versão inicial do backend Controle Financeiro Familiar
- Autenticação JWT com Flask-JWT-Extended
- CRUD completo para colaboradores, despesas, rendas, divisão mensal
- Cálculo de resumo financeiro mensal
- Integração com PostgreSQL (Supabase/Render) via psycopg2
- Deploy configurado para Render

---

## Guia de Versionamento

- **MAJOR** (X.0.0): Mudanças incompatíveis na API
- **MINOR** (0.X.0): Novas funcionalidades compatíveis
- **PATCH** (0.0.X): Correções de bugs compatíveis

Para releases futuras, mover itens de `[Unreleased]` para uma nova seção versionada `[X.Y.Z] - YYYY-MM-DD`.