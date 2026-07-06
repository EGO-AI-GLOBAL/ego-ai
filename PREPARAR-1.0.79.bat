@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.79 — IAP iOS + PAUSA livre

echo.
echo ============================================================
echo   PREPARAR 1.0.79 — fix IAP App Store + PAUSA 20 tecnicas
echo ============================================================
echo.
echo  app.config.ts version = "1.0.79" · iOS 77 · Android 124
echo.
echo  1. DEPLOY-API-PAUSA-LIVRE.bat  (Railway ~2 min)
echo  2. git pull ^&^& commit ja feito — confirme push origin main
echo  3. Amanha: GERAR-1.0.79.bat
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
echo OK — corra DEPLOY-API-PAUSA-LIVRE.bat e depois GERAR-1.0.79.bat
pause
