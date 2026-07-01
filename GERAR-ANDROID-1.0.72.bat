@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.72 — só Android

echo.
echo ============================================================
echo   EGO-AI 1.0.72 — BUILD SÓ ANDROID (iOS aguarda App Store)
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
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-android --ids-file builds-1.0.72.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-ANDROID-1.0.72.bat
echo iOS: quando Apple aprovar — GERAR-1.0.72.bat (iOS+Android) ou só iOS
pause
