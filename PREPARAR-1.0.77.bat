@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.77 — pack visual + Monstrinhos F10 + PAUSA v2

echo.
echo ============================================================
echo   PREPARAR 1.0.77 — visual premium + Fase 10 + PAUSA v2
echo ============================================================
echo.
echo  app.config.ts version = "1.0.77" · iOS 75 · Android 122
echo  Railway: EGO_PLAY_INTEGRITY_MODE=enforce (recomendado)
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
echo OK — pode GERAR-1.0.77.bat
pause
