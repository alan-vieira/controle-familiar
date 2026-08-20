# scripts/check-coverage.ps1
# Roda TODOS os testes (incluindo os novos) e gera relatório de coverage

$ErrorActionPreference = "Continue"

Write-Host "[COV] Iniciando ambiente de teste..." -ForegroundColor Yellow
& "$PSScriptRoot\test-setup.ps1"

Write-Host "[COV] Executando testes com coverage..." -ForegroundColor Yellow

# Carrega variaveis
Get-Content .env.testing | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

# Roda pytest com coverage detalhado
pytest --cov=app --cov=routes --cov=utils --cov=connection --cov-report=term-missing --cov-report=html

$TEST_EXIT = $LASTEXITCODE

Write-Host "[COV] Limpando ambiente..." -ForegroundColor Yellow
& "$PSScriptRoot\test-teardown.ps1"

if ($TEST_EXIT -eq 0) {
    Write-Host ""
    Write-Host "[OK] Relatorio HTML gerado em: htmlcov\index.html" -ForegroundColor Green
    Write-Host "[OK] Abra no navegador para ver cobertura linha-a-linha" -ForegroundColor Green
}

exit $TEST_EXIT