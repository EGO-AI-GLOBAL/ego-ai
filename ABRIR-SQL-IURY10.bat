@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Criar cupom IURY10 — Supabase

echo.
echo 1) Abra o Supabase SQL Editor
echo 2) Cole o ficheiro: supabase\CRIAR-PARCEIRO-IURY10.sql
echo 3) RUN
echo.
start "" "https://supabase.com/dashboard/project/_/sql/new"
notepad "supabase\CRIAR-PARCEIRO-IURY10.sql"
pause
