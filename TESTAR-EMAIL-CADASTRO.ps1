# Testa e-mail de boas-vindas na API (Railway) — sem colar chave no historico do PowerShell.
$ErrorActionPreference = "Stop"
$api = "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/test-signup-email"

Write-Host ""
Write-Host "=== EGO-AI — testar e-mail de cadastro ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "A chave NAO e o texto 'SUA_REFERRAL_ADMIN_SECRET' nem 'VALOR_DO_...'." -ForegroundColor Yellow
Write-Host "Copie o VALOR REAL em Railway -> servico API -> Variables -> REFERRAL_ADMIN_SECRET"
Write-Host "(ou EGO_ADMIN_API_KEY, se for esse o nome la)."
Write-Host ""

$adminKey = Read-Host "Cole a chave admin do Railway (nao aparece enquanto digita)"
if (-not $adminKey.Trim()) {
    Write-Host "Cancelado — chave vazia." -ForegroundColor Red
    exit 1
}

$email = Read-Host "E-mail que vai RECEBER o teste (ex: seu@gmail.com)"
if ($email -notmatch "@") {
    Write-Host "E-mail invalido." -ForegroundColor Red
    exit 1
}

$nome = Read-Host "Seu nome (Enter = Iury)"
if (-not $nome.Trim()) { $nome = "Iury" }

$bodyObj = @{ email = $email.Trim(); full_name = $nome.Trim() }
$bodyJson = $bodyObj | ConvertTo-Json -Compress

$headers = @{
    "X-Admin-Key"    = $adminKey.Trim()
    "Content-Type"   = "application/json"
}

Write-Host ""
Write-Host "Enviando..." -ForegroundColor Gray
try {
    $resp = Invoke-RestMethod -Method POST -Uri $api -Headers $headers -Body $bodyJson
    Write-Host ""
    Write-Host "OK — e-mail enviado!" -ForegroundColor Green
    $resp | ConvertTo-Json
    Write-Host ""
    Write-Host "Verifique Entrada e Spam de: $email" -ForegroundColor Cyan
    Write-Host "Remetente esperado: contato@egoai.com.br"
}
catch {
    $msg = $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        try {
            $err = $_.ErrorDetails.Message | ConvertFrom-Json
            $msg = $err.error
        } catch {
            $msg = $_.ErrorDetails.Message
        }
    }
    Write-Host ""
    if ($msg -match "admin") {
        Write-Host "ERRO: chave admin errada." -ForegroundColor Red
        Write-Host "Railway -> Variables -> copie o VALOR de REFERRAL_ADMIN_SECRET (icone olho)."
        Write-Host "Se nao existir, crie a variavel, salve e aguarde redeploy."
    }
    elseif ($msg -match "SMTP") {
        Write-Host "ERRO SMTP: $msg" -ForegroundColor Red
        Write-Host "Confira EGO_SMTP_PASSWORD e porta 465/SSL no Railway."
    }
    else {
        Write-Host "ERRO: $msg" -ForegroundColor Red
    }
    exit 1
}
