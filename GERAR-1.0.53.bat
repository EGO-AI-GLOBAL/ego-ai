@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.53 HOTFIX — iOS 41 + Android 93

echo.
echo ============================================================
echo   EGO-AI 1.0.53 HOTFIX — crash pos-login isolado
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

python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.53.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-E-SUBMETER-1.0.53.bat
pause
