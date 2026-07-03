@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.76 — IAP iOS (App Store)

echo.
echo ============================================================
echo   PREPARAR 1.0.76 — In-App Purchase iOS
echo ============================================================
echo.
echo  app.config.ts version = "1.0.76"
echo  Railway: APPLE_IAP_SHARED_SECRET configurado
echo  Connect: 3 assinaturas criadas (Conexao, Premium, Total)
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
echo OK — pode GERAR-1.0.76.bat
pause
