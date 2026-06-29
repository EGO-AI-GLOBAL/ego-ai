@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Preparar 1.0.61 — hotfix voz Android JSON/base64

echo.
echo ============================================================
echo   PREPARAR 1.0.61 — voz Android JSON/base64 primeiro
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
echo OK — quando Release der verde (4x SYNC): GERAR-1.0.61.bat
pause
