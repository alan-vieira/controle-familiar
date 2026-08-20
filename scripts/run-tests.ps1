# scripts/run-tests.ps1
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Continue"

Write-Host "[RUN] Iniciando ambiente de teste..." -ForegroundColor Yellow
& "$PSScriptRoot\test-setup.ps1"

Write-Host "[RUN] Executando testes..." -ForegroundColor Yellow

# Carrega variaveis do .env.testing
Get-Content .env.testing | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

# Executa pytest com argumentos extras usando o python do venv
$venv_python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venv_python)) {
    Write-Host "[ERRO] Venv nao encontrado em $venv_python. Execute: python -m venv .venv" -ForegroundColor Red
    exit 1
}

if ($PytestArgs) {
    & $venv_python -m pytest @PytestArgs
} else {
    & $venv_python -m pytest
}
$TEST_EXIT = $LASTEXITCODE

Write-Host "[RUN] Limpando ambiente..." -ForegroundColor Yellow
& "$PSScriptRoot\test-teardown.ps1"

if ($TEST_EXIT -eq 0) {
    Write-Host "[OK] Todos os testes passaram!" -ForegroundColor Green
} else {
    Write-Host "[AVISO] Alguns testes falharam (exit code: $TEST_EXIT)" -ForegroundColor Yellow
}

exit $TEST_EXIT