#!/bin/bash
# scripts/test-teardown.sh
echo "🧹 Derrubando container PostgreSQL de teste..."
docker compose -f docker-compose.test.yml down -v
echo "✅ Container removido."