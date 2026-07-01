@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.72 — diário de humor 7 dias

echo.
echo ============================================================
echo   PREPARAR 1.0.72 — Fase 9b journal Monstrinhos
echo ============================================================
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
echo API: deploy Railway apos push (mood_journal no check-in)
echo Depois: GERAR-1.0.72.bat
pause
