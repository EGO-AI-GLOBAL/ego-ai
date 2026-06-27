@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Supabase — Redirect URLs (NAO e SQL)

echo.
echo ============================================================
echo   ATENCAO: NAO e SQL — NAO cole nada no SQL Editor
echo ============================================================
echo.
echo Isto e configuracao no PAINEL do Supabase:
echo   Authentication ^> URL Configuration ^> Redirect URLs
echo.
echo Abrindo guia com as 2 URLs para copiar...
echo.

start "" notepad "%~dp0supabase\SUPABASE-REDIRECT-RESET-SENHA.txt"

start "" "https://supabase.com/dashboard"

echo.
echo No Supabase: entre no projeto EGO-AI ^> Authentication ^> URL Configuration
echo Adicione as 2 URLs do Notepad (uma de cada vez) e Save.
echo.
pause
