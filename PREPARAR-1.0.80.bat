@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.80 — jardim humor primeiro

echo.
echo ============================================================
echo   PREPARAR 1.0.80 — Monstrinhos: humor antes das missões
echo ============================================================
echo.
echo  app.config.ts version = "1.0.80" · iOS 78 · Android 125
echo.
echo  Sem deploy API obrigatório (só UI jardim).
echo  PAUSA EGO / IAP — não mexer; já está na 1.0.79.
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
echo OK — amanha: GERAR-1.0.80.bat
pause
