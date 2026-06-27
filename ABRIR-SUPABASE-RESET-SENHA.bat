@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Supabase — Redirect URLs reset senha

echo.
echo Cole estas URLs no Supabase:
echo   Authentication ^> URL Configuration ^> Redirect URLs
echo.

start "" notepad "%~dp0supabase\SUPABASE-REDIRECT-RESET-SENHA.txt"

start "" "https://supabase.com/dashboard/project/_/auth/url-configuration"

pause
