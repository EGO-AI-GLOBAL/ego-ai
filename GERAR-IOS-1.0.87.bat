@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar iOS 1.0.87

echo.
echo ============================================================
echo   EGO-AI 1.0.87 — iOS (EULA 3.1.2c + nova versao Apple)
echo ============================================================
echo   iOS build 89 · depois AGUARDAR-IOS-E-SUBMETER-1.0.87.bat
echo.

call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --skip-sync --ids-file builds-1.0.87.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-IOS-E-SUBMETER-1.0.87.bat
echo Connect: + Versao 1.0.87 + build 89 — ver marketing\NOTAS-1.0.87-APP-STORE.txt
pause
