@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.82 — iOS ficha App Store

echo.
echo ============================================================
echo   PREPARAR 1.0.82 — iOS-only ficha PAUSA EGO
echo ============================================================
echo.
echo  app.config.ts version = "1.0.82" · iOS 83 · Android sem build
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
echo OK — a seguir: GERAR-IOS-1.0.82.bat
pause
