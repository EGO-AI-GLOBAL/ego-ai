@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.84 — Tríade Silenciosa

echo.
echo ============================================================
echo   PREPARAR 1.0.84 — iOS auto + Android manual
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
echo OK — a seguir: GERAR-1.0.84.bat
pause
