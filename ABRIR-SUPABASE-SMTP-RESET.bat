@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Supabase — SMTP reset senha (NAO e SQL)

echo.
echo ============================================================
echo   SMTP no Supabase — e-mail «Esqueci a senha» (NAO e SQL)
echo ============================================================
echo.
echo   SQL Editor     = APAGAR-CONTA, CRESCIMENTO...
echo   SMTP + Redirect = PAINEL Supabase (guias no Notepad)
echo.

start "" notepad "%~dp0supabase\SUPABASE-SMTP-RESET-SENHA.txt"
start "" notepad "%~dp0supabase\SUPABASE-REDIRECT-RESET-SENHA.txt"
start "" "https://supabase.com/dashboard"

echo.
echo 1. SMTP Settings (Custom SMTP Brevo)
echo 2. Redirect URLs (2 links)
echo.
pause
