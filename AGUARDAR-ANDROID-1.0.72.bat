@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar Android 1.0.72

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --android-only --ids-file builds-1.0.72.ids.json
pause
