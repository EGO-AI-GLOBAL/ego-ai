@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.54 HOTFIX — iOS 42 + Android 94

echo.
echo ============================================================
echo   EGO-AI 1.0.54 HOTFIX — persona Keychain após reinstall
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

python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.54.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-E-SUBMETER-1.0.54.bat
pause
