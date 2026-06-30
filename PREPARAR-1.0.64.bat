@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Preparar 1.0.64 — voz revert + anti-loop

echo.
echo ============================================================
echo   PREPARAR 1.0.64 — voz como 1.0.61 + trava envio duplo
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
echo OK — depois: GERAR-1.0.64.bat
pause
