@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — criar cupom parceiro

echo.
echo Precisa SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY no .env
echo.
set /p CODIGO="Codigo cupom (ex. MARIA10): "
set /p NOME="Nome parceiro: "
set /p EMAIL="E-mail: "
set /p PIX="PIX repasse: "

python scripts\create_referral_partner.py --code "%CODIGO%" --name "%NOME%" --email "%EMAIL%" --pix "%PIX%"
pause
