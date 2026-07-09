@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.83 — Jardim da Gentileza + iOS ASO

echo.
echo ============================================================
echo   PREPARAR 1.0.83 — Jardim da Gentileza (iOS only)
echo ============================================================
echo.
echo  app.config.ts version = "1.0.83" · iOS build 85 · Android 126 (sem build)
echo.
echo  API: ego_api/gentleness.py + POST daily-care/calm-mark (deploy ANTES do build).
echo  iOS: subtitulo ASO + Jardim da Gentileza na mesma release.
echo.

call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo OK — depois: GERAR-1.0.83.bat (so iOS)
pause
