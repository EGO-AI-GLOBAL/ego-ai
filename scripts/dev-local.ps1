# EGO-AI — verifica .env e lembra como iniciar dev local (não inicia servidores automaticamente)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== EGO-AI — desenvolvimento local ===" -ForegroundColor Cyan
Write-Host ""

$verify = & python "$Root\scripts\verify_env.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Corrija .env antes de continuar. Veja CONFIGURACAO.md" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Abra DOIS terminais:" -ForegroundColor Green
Write-Host ""
Write-Host "  Terminal 1 (API):" -ForegroundColor White
Write-Host "    cd `"$Root`""
Write-Host "    python flask_api.py"
Write-Host ""
Write-Host "  Terminal 2 (App):" -ForegroundColor White
Write-Host "    cd `"$Root\app`""
Write-Host "    npx expo start --web --clear"
Write-Host ""
Write-Host "  Browser: tecla w  |  Telefone: Expo Go + QR" -ForegroundColor Gray
Write-Host "  Guia completo: COMO_LANCAR.md" -ForegroundColor Gray
