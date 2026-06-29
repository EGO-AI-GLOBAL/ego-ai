@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Supabase — apagar conta Sheila (cadastro novo)

echo.
echo E-mail: kta.sheila28@gmail.com
echo.
echo 1. Abre o Supabase SQL Editor
echo 2. Cole APAGAR-CONTA-SHEILA.sql
echo 3. RUN — ultima query deve voltar 0 linhas
echo.

start "" notepad "%~dp0supabase\APAGAR-CONTA-SHEILA.sql"
start "" "https://supabase.com/dashboard/project/_/sql/new"

pause
