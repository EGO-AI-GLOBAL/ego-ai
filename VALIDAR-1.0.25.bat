@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI 1.0.25 — validar iOS + Android

echo.
echo ============================================================
echo   EGO-AI 1.0.25 — Descarrego da noite + Lista de compras
echo ============================================================
echo.
echo ANTES do build:
echo   1. Supabase: rode supabase\COLE-1.0.25-DESCARREGO-COMPRAS.sql
echo   2. Railway: git push (api_build 2026-06-01-1.0.25-habits)
echo   3. VERIFICAR-ANTES-DEPLOY.bat
echo.
echo DEPOIS do build:
echo   Android: .aab na Play (teste fechado)
echo   iOS: TestFlight build 4
echo.

start "" notepad "%CD%\marketing\VALIDAR-1.0.25.txt"
start "" notepad "%CD%\supabase\COLE-1.0.25-DESCARREGO-COMPRAS.sql"
start "" "https://supabase.com/dashboard"
start "" "https://railway.app/dashboard"
start "" "https://appstoreconnect.apple.com/apps/6780595396/testflight/ios"
start "" "https://play.google.com/console"

echo Abri: SQL 1.0.25, notas da versao, Supabase, Railway, TestFlight, Play.
echo.
pause
