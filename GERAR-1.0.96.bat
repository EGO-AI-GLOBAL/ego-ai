@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.96 — só Android (API 36)
call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-android --ids-file builds-1.0.96.ids.json
if errorlevel 1 ( pause & exit /b 1 )
echo Depois: wait-submit --android-only
pause
