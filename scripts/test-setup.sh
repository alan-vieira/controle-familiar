#!/bin/bash
# scripts/test-setup.sh
# Sobe o container PostgreSQL de teste e executa migrations (Git Bash/WSL)

set -e

echo "🐳 Subindo container PostgreSQL de teste..."
docker compose -f docker-compose.test.yml up -d

echo "⏳ Aguardando banco ficar pronto..."
retries=0
while ! docker compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U test_user >/dev/null 2>&1; do
    sleep 1
    retries=$((retries + 1))
    if [ $retries -ge 30 ]; then
        echo "❌ Timeout: banco não ficou pronto em 30s"
        exit 1
    fi
done

echo "✅ Banco pronto!"
echo "📊 Verificando migrations..."
docker compose -f docker-compose.test.yml exec -T postgres-test psql -U test_user -d controle_familiar_test -c "SELECT 'Migrations OK' AS status;"

echo "🧪 Ambiente de teste pronto!"
echo ""
echo "Comandos úteis:"
echo "  Rodar testes:     pytest"
echo "  Ver logs:         docker compose -f docker-compose.test.yml logs -f"
echo "  Parar banco:      docker compose -f docker-compose.test.yml down"
echo "  Resetar banco:    ./scripts/test-teardown.sh; ./scripts/test-setup.sh"