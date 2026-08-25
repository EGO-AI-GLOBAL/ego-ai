@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.115 — Android (Play Billing 8 + API 36)
call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-android --ids-file builds-1.0.115.ids.json
if errorlevel 1 ( pause & exit /b 1 )
echo Depois: AGUARDAR-ANDROID-1.0.115.bat (AAB manual Play)
pause
