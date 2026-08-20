# scripts/test-setup.ps1
# Sobe o container PostgreSQL de teste e executa migrations

$ErrorActionPreference = "Continue"

Write-Host "[SETUP] Subindo container PostgreSQL de teste..." -ForegroundColor Yellow
docker compose -f docker-compose.test.yml up -d 2>$null

Write-Host "[SETUP] Aguardando banco ficar pronto..." -ForegroundColor Yellow
$retries = 0
$ready = $false
do {
    Start-Sleep -Seconds 1
    $retries++
    $status = docker compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U test_user 2>$null
    if ($LASTEXITCODE -eq 0 -and $status -match "accepting connections") {
        $ready = $true
        break
    }
} until ($retries -ge 30)

if (-not $ready) {
    Write-Host "[ERRO] Timeout: banco nao ficou pronto em 30s" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Banco pronto!" -ForegroundColor Green
Write-Host "[SETUP] Verificando migrations..." -ForegroundColor Yellow

docker compose -f docker-compose.test.yml exec -T postgres-test psql `
    -U test_user -d controle_familiar_test `
    -c "SELECT 'Migrations OK' AS status;" 2>$null

Write-Host ""
Write-Host "Ambiente de teste pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos uteis:" -ForegroundColor Cyan
Write-Host "  Rodar testes:     pytest"
Write-Host "  Ver logs:         docker compose -f docker-compose.test.yml logs -f"
Write-Host "  Parar banco:      docker compose -f docker-compose.test.yml down"
Write-Host "  Resetar banco:    .\scripts\test-teardown.ps1; .\scripts\test-setup.ps1"