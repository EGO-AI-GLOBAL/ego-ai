@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.74 — diario de humor (#16)

echo.
echo ============================================================
echo   PREPARAR 1.0.74 — Fase 9b journal completo
echo ============================================================
echo.
echo  Antes: app.config.ts version = "1.0.74"
echo  Depois: DEPLOY API Railway (journal-note + nota no check-in)
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
echo OK — pode GERAR-1.0.74.bat
pause
