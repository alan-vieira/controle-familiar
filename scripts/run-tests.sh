#!/bin/bash
# scripts/run-tests.sh
# One-command test runner (Git Bash/WSL)

set -e

echo "🐳 Iniciando ambiente de teste..."
./scripts/test-setup.sh

echo "🧪 Executando testes..."

# Carrega variáveis do .env.testing
export $(grep -v '^#' .env.testing | xargs)

# Executa pytest com argumentos extras
pytest "$@"
TEST_EXIT=$?

echo "🧹 Limpando ambiente..."
./scripts/test-teardown.sh

if [ $TEST_EXIT -eq 0 ]; then
    echo "✅ Todos os testes passaram!"
else
    echo "⚠️  Alguns testes falharam (exit code: $TEST_EXIT)"
fi

exit $TEST_EXIT