@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.78 — push PAUSA + tap notificação

echo.
echo ============================================================
echo   PREPARAR 1.0.78 — push PAUSA 10h/18h + app notificações
echo ============================================================
echo.
echo  app.config.ts version = "1.0.78" · iOS 76 · Android 123
echo  Railway: deploy API com pausa_push (funciona antes do build)
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
echo OK — amanhã: GERAR-1.0.78.bat
pause
