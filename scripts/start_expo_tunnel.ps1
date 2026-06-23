# Expo com túnel HTTPS — microfone no iPhone Safari (mensagem de voz).
# Requer: python flask_api.py a correr no PC (porta 5000).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root "app"

Write-Host "A iniciar Expo com túnel HTTPS (microfone no iPhone)..." -ForegroundColor Cyan
Write-Host "Confirme que a API Flask está a correr: python flask_api.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "Link ngrok expira quando fecha este terminal." -ForegroundColor DarkGray
Write-Host "Para o link antigo (Wi‑Fi): scripts\\start_expo_lan.ps1" -ForegroundColor DarkGray
Write-Host ""
Write-Host "No iPhone, abra o link https://… que aparecer abaixo (só para voz)." -ForegroundColor Green
Write-Host ""

Set-Location $appDir
npx expo start --tunnel --port 8081
