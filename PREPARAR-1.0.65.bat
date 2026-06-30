@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Preparar 1.0.65 — revert voz 26/06

echo.
echo ============================================================
echo   PREPARAR 1.0.65 — voz como 26/06 (antes do bug 1.0.62)
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
echo OK — depois: GERAR-1.0.65.bat
pause
