# Testa webhook Discord — uso:
#   $env:ERROR_ALERT_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
#   .\scripts\test_discord_webhook.ps1

param(
    [string]$Url = $env:ERROR_ALERT_WEBHOOK_URL
)

if (-not $Url) {
    Write-Host "Defina ERROR_ALERT_WEBHOOK_URL ou passe -Url" -ForegroundColor Red
    exit 1
}

$body = @{
    content = "EGO-AI — teste de alerta $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Se viu isto no Discord, esta OK."
} | ConvertTo-Json -Compress

try {
    Invoke-RestMethod -Uri $Url -Method Post -Body $body -ContentType "application/json"
    Write-Host "OK — mensagem enviada ao Discord." -ForegroundColor Green
} catch {
    Write-Host "Falhou: $_" -ForegroundColor Red
    exit 1
}
