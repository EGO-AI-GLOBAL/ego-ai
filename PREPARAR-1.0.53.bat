@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Preparar 1.0.53 HOTFIX — login/chat crash

echo.
echo ============================================================
echo   PREPARAR 1.0.53 — crash login + widgets isolados
echo ============================================================
echo.

python scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo OK — quando quiser: GERAR-1.0.53.bat
pause
