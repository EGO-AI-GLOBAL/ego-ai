@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.83 — Jardim da Gentileza (iOS only)



echo.

echo ============================================================

echo   EGO-AI 1.0.83 — Jardim da Gentileza + ASO iOS

echo ============================================================

echo.

echo  SO iOS — Android NAO nesta release (Marketing).

echo  Build 85 (build 84 nao tinha Jardim da Gentileza).

echo.



call _ego_run_python.bat scripts\onboarding_guard.py

if errorlevel 1 ( pause & exit /b 1 )

call _ego_run_python.bat scripts\regression_guard.py

if errorlevel 1 ( pause & exit /b 1 )

call _ego_run_python.bat scripts\smoke_test_api.py

if errorlevel 1 ( pause & exit /b 1 )

call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check

if errorlevel 1 ( pause & exit /b 1 )

call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --ids-file builds-1.0.83.ids.json

if errorlevel 1 ( pause & exit /b 1 )



echo.

echo Depois: AGUARDAR-E-SUBMETER-1.0.83.bat

pause

