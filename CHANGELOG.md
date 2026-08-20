# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.4.0] - 2026-08-21

### Added
- **Suite de Testes Abrangente**: 156 testes automatizados (pytest) cobrindo autenticação, CRUD, validações de negócio, handlers de erro e edge cases.
- **CI/CD com GitHub Actions**: Pipeline automatizado (`.github/workflows/tests.yml`) que executa testes a cada push/PR.
- **Gate de Qualidade**: Configuração `--cov-fail-under=85` no CI para bloquear merges que reduzam a cobertura de código.
- **Ambiente de Teste Isolado**: Configuração Docker (`docker-compose.test.yml`) com PostgreSQL 15.6-alpine idêntico ao de produção.
- **Scripts de Automação**: Scripts PowerShell (`scripts/check-coverage.ps1`, `run-tests.ps1`, etc.) para setup, teardown e execução de testes com relatório de cobertura.
- **Badges de Status**: Adicionados badges de "Tests & Coverage" e "Coverage 85%" no `README.md`.

### Changed
- Ajuste nos fixtures de teste para compatibilidade total com `psycopg2.extras.RealDictCursor` (acesso via chaves de dicionário em vez de índices).
- Refinamento dos testes de handlers JWT para validar corretamente os campos `error` e `msg` nas respostas da API.

### Security
- Garantia de que exceções não tratadas (500) retornam JSON genérico sem vazar stack traces em ambiente de produção.
- Proteção contra regressão de lógica financeira (precisão Decimal) e regras de negócio (integridade referencial) via testes automatizados.

---

## [0.3.0] - 2026-08-15

### Security
- Dependências atualizadas (CVEs): Werkzeug >=3.1.6, gunicorn >=23.0.0,
  Flask-CORS >=5.0.0, Flask >=3.1.0.
- Rate limiting em `/api/auth/login` e `/api/auth/register` (10 req/min).
- Headers de segurança: X-Content-Type-Options, X-Frame-Options,
  Referrer-Policy e HSTS (produção).

### Fixed
- Pool de conexões não é mais fechado a cada request: `close_pool()`
  movido de `teardown_appcontext` para `atexit`.
- Blacklist de tokens agora em tabela `token_blacklist` (PostgreSQL) —
  funciona com múltiplos workers (antes: memória por processo).

### Changed
- Callback da blocklist registrado no `create_app()` (antes: `record_once`).
- gunicorn: `--timeout 60 --preload` (cold start do Render free).

### Added
- `migrations/002_token_blacklist.sql`.

---

## [0.2.0] - 2026-08-08

**Fase 3: Precisão Financeira e Integridade de Dados**

### Added
- **`utils/json_utils.py`** com `DecimalEncoder` para serialização JSON precisa de valores monetários (Decimal como string)
- **Helper `json_response()`** que usa o encoder customizado em todas as rotas
- **Validação de data futura** em despesas: bloqueia com código `FUTURE_DATE` (HTTP 400)
- **Validação de integridade referencial** no DELETE de colaboradores:
  - Código `HAS_EXPENSES` (HTTP 409) se o colaborador tem despesas vinculadas
  - Código `HAS_INCOMES` (HTTP 409) se o colaborador tem rendas vinculadas
- **Tratamento de centavos residuais** em divisão proporcional no resumo (ex: R$ 100,00 / 3 pessoas fecha em exatamente R$ 100,00)
- **Adapter Decimal ↔ NUMERIC** em `connection.py` via `psycopg2.extensions.register_adapter`
- **Migração SQL** `migrations/001_add_indexes.sql` com índices de performance:
  - `idx_despesa_mes_vigente`
  - `idx_despesa_colaborador_mes`
  - `idx_renda_mes_ano`
  - `idx_renda_colaborador_mes`

### Changed
- **Migração completa de `float` para `Decimal`** em todas as rotas que manipulam valores monetários:
  - `routes/despesas.py`: criação, atualização e serialização
  - `routes/rendas.py`: validação e armazenamento
  - `routes/resumo.py`: soma, porcentagem e divisão
- **Otimização N+1** no endpoint de resumo: substituído loop de N queries por uma única query com `GROUP BY colaborador_id`
- Todas as rotas passam a usar `json_response()` em vez de `jsonify` direto
- Arredondamento com `Decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)` em vez de `round(..., 2)` em float

### Fixed
- **Erro de precisão** `0.1 + 0.2 = 0.30000000000000004` resolvido com `Decimal(str(valor))`
- **Drift de centavos** em soma de múltiplas despesas eliminado
- **Divisão proporcional** agora distribui centavo residual no último colaborador (soma das partes = total exato)
- **`KeyError: 0`** no DELETE de colaboradores com `RealDictCursor` corrigido (acesso por chave `'total'` em vez de índice `[0]`)

### Security
- Bloqueio de exclusão de colaboradores com dados financeiros vinculados (protege integridade referencial)
- Rejeição de despesas com datas futuras (previne fraude/erro de datas)
- Valores monetários serializados como string preservam precisão exata no JSON

---

## [0.1.0] - 2026-08-07

**Fase 1 & 2: Foundation Segura e Autenticação**

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
- **Hash de senha com PBKDF2** (via Werkzeug)
- **Blacklist de tokens JWT** (logout real)
- **Refresh token** para renovação de sessão

### Changed
- **`app.py`**: Corrigido `Flask(name)` → `Flask(__name__)` e `if name == 'main':` → `if __name__ == '__main__':`
- **`app.py`**: Removido recriação da app a cada request no handler WSGI
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
- **Indentação**: Corrigidas indentações inconsistentes em `app.py`
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

## [0.0.0-baseline] - 2025-11-24

Snapshot inicial do projeto antes da refatoração. Código legado com problemas de sintaxe, segurança e conexão que foram endereçados nas versões subsequentes.

---

## Guia de Versionamento

- **MAJOR** (X.0.0): Mudanças incompatíveis na API
- **MINOR** (0.X.0): Novas funcionalidades compatíveis
- **PATCH** (0.0.X): Correções de bugs compatíveis

Para releases futuras, mover itens de `[Unreleased]` para uma nova seção versionada `[X.Y.Z] - YYYY-MM-DD`.