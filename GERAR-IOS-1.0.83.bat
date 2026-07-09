@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar iOS 1.0.83

echo.
echo ============================================================
echo   EGO-AI 1.0.83 — iOS-only subtítulo + idioma PT-BR
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
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --ids-file builds-1.0.83.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-IOS-E-SUBMETER-1.0.83.bat
pause
