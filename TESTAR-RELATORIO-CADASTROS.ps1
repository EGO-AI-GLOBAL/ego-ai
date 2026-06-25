# Envia relatório diário de cadastros (API Railway ou local)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$api = "https://ego-ai-production-a2c2.up.railway.app"
$adminKey = $env:REFERRAL_ADMIN_SECRET
if (-not $adminKey) {
    $envFile = Join-Path $PSScriptRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*REFERRAL_ADMIN_SECRET\s*=\s*(.+)\s*$') {
                $adminKey = $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}

Write-Host ""
Write-Host "=== EGO-AI — relatório diário de cadastros ===" -ForegroundColor Cyan
Write-Host ""

if ($adminKey) {
    Write-Host "A chamar API (produção)..." -ForegroundColor Yellow
    $headers = @{
        "X-Admin-Key" = $adminKey
        "Content-Type" = "application/json"
    }
    try {
        $resp = Invoke-RestMethod -Method Post -Uri "$api/api/v1/admin/cron/daily-stats" -Headers $headers -Body "{}"
        $resp | ConvertTo-Json -Depth 6
        if ($resp.ok -and $resp.sent) {
            Write-Host ""
            Write-Host "E-mail enviado para: $($resp.recipient)" -ForegroundColor Green
        } elseif ($resp.ok -and -not $resp.sent) {
            Write-Host ""
            Write-Host "OK (dry-run ou sem envio)." -ForegroundColor Green
        }
        exit 0
    } catch {
        Write-Host "API falhou: $_" -ForegroundColor Red
        Write-Host "Tentando local (python + .env)..." -ForegroundColor Yellow
    }
}

python scripts\send_daily_stats_now.py
exit $LASTEXITCODE
