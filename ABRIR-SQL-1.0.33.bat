@echo off
chcp 65001 >nul
cd /d "%~dp0"
title SQL 1.0.33 — Entre Nos

echo Cole no Supabase SQL Editor:
echo   supabase\COLE-1.0.33-ENTRE-NOS.sql
echo.
type "%~dp0supabase\COLE-1.0.33-ENTRE-NOS.sql" | clip
echo SQL copiado para a area de transferencia.
start "" notepad "%~dp0supabase\COLE-1.0.33-ENTRE-NOS.sql"
pause
