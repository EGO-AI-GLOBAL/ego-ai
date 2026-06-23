# Mostra o link certo para o iPhone (o IP da Wi-Fi muda quando troca de rede).

$ip = (
  Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
      ($_.InterfaceAlias -match 'Wi-Fi|Wireless|WLAN|Ethernet')
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
)

$expo = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
$api = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== EGO-AI - link para o iPhone (mesma Wi-Fi) ===" -ForegroundColor Cyan
Write-Host ""

if (-not $ip) {
  Write-Host "IP não encontrado. Rode: ipconfig" -ForegroundColor Red
  exit 1
}

Write-Host "IP atual do PC: $ip" -ForegroundColor Yellow
Write-Host ""
Write-Host "Abra no Safari do iPhone:" -ForegroundColor Green
Write-Host "  http://${ip}:8081" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""

if (-not $expo) {
  Write-Host "Expo NÃO está a correr na porta 8081." -ForegroundColor Red
  Write-Host "  Execute: .\scripts\start_expo_lan.ps1" -ForegroundColor Yellow
} else {
  Write-Host "Expo: a correr (porta 8081)" -ForegroundColor Green
}

if (-not $api) {
  Write-Host "API Flask NÃO está a correr na porta 5000." -ForegroundColor Red
  Write-Host "  Execute: python flask_api.py" -ForegroundColor Yellow
} else {
  Write-Host "API:  a correr (porta 5000)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Se usava http://192.168.3.19:8081 - o IP mudou. Use so o link acima." -ForegroundColor DarkGray
Write-Host "Guarde este link novo; o IP muda se trocar de Wi-Fi." -ForegroundColor DarkGray
Write-Host ""
