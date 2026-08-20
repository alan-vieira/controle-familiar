# scripts/check-env.ps1
# Verifica todas as dependencias antes de rodar os testes

$ErrorActionPreference = "Continue"
$allOk = $true

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CHECKLIST DE AMBIENTE - Controle Familiar " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Diretorio atual
Write-Host "[1/7] Diretorio atual:" -ForegroundColor Yellow
$pwd = Get-Location
Write-Host "  $pwd"
if ($pwd.Path -ne "D:\projetos_dev\controle-familiar") {
    Write-Host "  [AVISO] Voce nao esta no diretorio do projeto!" -ForegroundColor Red
    Write-Host "  Execute: cd D:\projetos_dev\controle-familiar" -ForegroundColor Red
    $allOk = $false
} else {
    Write-Host "  [OK]" -ForegroundColor Green
}
Write-Host ""

# 2. venv ativo
Write-Host "[2/7] venv ativo:" -ForegroundColor Yellow
$venvActive = $env:VIRTUAL_ENV
if ($venvActive) {
    Write-Host "  $venvActive" -ForegroundColor Green
    Write-Host "  [OK]" -ForegroundColor Green
} else {
    Write-Host "  [ERRO] venv NAO esta ativo!" -ForegroundColor Red
    Write-Host "  Execute: .\venv\Scripts\Activate.ps1" -ForegroundColor Red
    $allOk = $false
}
Write-Host ""

# 3. Python correto
Write-Host "[3/7] Python em uso:" -ForegroundColor Yellow
$pythonPath = (Get-Command python).Source
Write-Host "  $pythonPath"
if ($pythonPath -like "*controle-familiar*venv*") {
    Write-Host "  [OK] Python do venv" -ForegroundColor Green
} else {
    Write-Host "  [AVISO] Python pode nao ser do venv" -ForegroundColor Yellow
}
Write-Host ""

# 4. PyJWT instalado
Write-Host "[4/7] PyJWT instalado:" -ForegroundColor Yellow
try {
    $jwtInfo = pip show PyJWT 2>&1
    if ($jwtInfo -match "Name: PyJWT") {
        $version = ($jwtInfo | Select-String "Version:").ToString().Split(":")[1].Trim()
        Write-Host "  Versao: $version" -ForegroundColor Green
        Write-Host "  [OK]" -ForegroundColor Green
    } else {
        Write-Host "  [ERRO] PyJWT NAO instalado!" -ForegroundColor Red
        Write-Host "  Execute: pip install PyJWT" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "  [ERRO] Falha ao verificar PyJWT" -ForegroundColor Red
    $allOk = $false
}
Write-Host ""

# 5. Import jwt
Write-Host "[5/7] Import jwt (Python):" -ForegroundColor Yellow
try {
    $result = python -c "import jwt; print('PyJWT OK:', jwt.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  $result" -ForegroundColor Green
        Write-Host "  [OK]" -ForegroundColor Green
    } else {
        Write-Host "  [ERRO] Falha no import jwt" -ForegroundColor Red
        Write-Host "  $result" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "  [ERRO] Excecao ao importar jwt" -ForegroundColor Red
    $allOk = $false
}
Write-Host ""

# 6. Docker Desktop
Write-Host "[6/7] Docker Desktop:" -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  $dockerVersion" -ForegroundColor Green
        Write-Host "  [OK]" -ForegroundColor Green
    } else {
        Write-Host "  [ERRO] Docker nao esta rodando!" -ForegroundColor Red
        Write-Host "  Abra o Docker Desktop e aguarde iniciar" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "  [ERRO] Docker nao encontrado" -ForegroundColor Red
    $allOk = $false
}
Write-Host ""

# 7. Docker Compose
Write-Host "[7/7] Docker Compose:" -ForegroundColor Yellow
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  $composeVersion" -ForegroundColor Green
        Write-Host "  [OK]" -ForegroundColor Green
    } else {
        Write-Host "  [ERRO] Docker Compose nao disponivel!" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "  [ERRO] Docker Compose nao encontrado" -ForegroundColor Red
    $allOk = $false
}
Write-Host ""

# Resultado final
Write-Host "============================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "  [OK] TODAS AS VERIFICACOES PASSARAM!" -ForegroundColor Green
    Write-Host "  Pode rodar: .\scripts\run-tests.ps1" -ForegroundColor Green
} else {
    Write-Host "  [ERRO] Algumas verificacoes falharam" -ForegroundColor Red
    Write-Host "  Corrija os itens acima antes de continuar" -ForegroundColor Red
}
Write-Host "============================================" -ForegroundColor Cyan