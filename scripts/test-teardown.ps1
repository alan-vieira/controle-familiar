# scripts/test-teardown.ps1
Write-Host "[TEARDOWN] Derrubando container PostgreSQL de teste..." -ForegroundColor Yellow
docker compose -f docker-compose.test.yml down -v
Write-Host "[OK] Container removido." -ForegroundColor Green