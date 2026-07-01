@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.72 — só iOS (App Store sem IAP)

echo.
echo ============================================================
echo   EGO-AI 1.0.72 — BUILD SÓ iOS (build 60, sem Stripe no app)
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
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --ids-file builds-1.0.72.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-IOS-1.0.72.bat
echo App Store Connect: build 60 + notas APP-STORE-IOS-SEM-IAP.txt
pause
