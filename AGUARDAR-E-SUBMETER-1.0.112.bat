@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar 1.0.112 — iOS auto, Android manual
call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.112.ids.json
if errorlevel 1 pause & exit /b 1
echo iOS submetido (TestFlight). Android manual quando AAB terminar.
pause
