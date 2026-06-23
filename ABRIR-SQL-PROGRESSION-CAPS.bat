@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Abrir COLE-PROGRESSION-CAPS.sql no Supabase SQL Editor
echo.
type supabase\COLE-PROGRESSION-CAPS.sql
echo.
echo Copie o conteudo acima para: Supabase - SQL Editor - Run
pause
