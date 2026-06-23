# Expo na rede local (link antigo) — iPhone + PC na mesma Wi‑Fi.
# Requer: python flask_api.py a correr no PC (porta 5000).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root "app"

$ip = (
  Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
      ($_.InterfaceAlias -match 'Wi-Fi|Wireless|WLAN|Ethernet')
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
)

Write-Host "A iniciar Expo na rede local (link antigo)..." -ForegroundColor Cyan
Write-Host "Confirme que a API Flask está a correr: python flask_api.py" -ForegroundColor Yellow
Write-Host ""
if ($ip) {
  Write-Host "No iPhone (Safari), abra:" -ForegroundColor Green
  Write-Host "  http://${ip}:8081" -ForegroundColor White -BackgroundColor DarkGreen
  Write-Host ""
  Write-Host "No PC:" -ForegroundColor Green
  Write-Host "  http://localhost:8081" -ForegroundColor White
} else {
  Write-Host "Não detetei o IP. No iPhone use http://SEU_IP:8081 (veja ipconfig)." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Se usava http://192.168.3.19:8081 - o IP mudou. Use so o link acima." -ForegroundColor Yellow
Write-Host "Para ver o link sem reiniciar: .\scripts\mostrar_link_iphone.ps1" -ForegroundColor DarkGray
Write-Host ""

Set-Location $appDir
npx expo start --host lan --port 8081
