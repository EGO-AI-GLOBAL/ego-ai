@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar Android 1.0.115 — AAB manual
call _ego_run_python.bat scripts\wait_and_submit_eas.py android-manual --ids-file builds-1.0.115.ids.json
if errorlevel 1 pause & exit /b 1
pause
