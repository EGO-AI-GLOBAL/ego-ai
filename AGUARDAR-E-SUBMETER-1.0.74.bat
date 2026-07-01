@echo off
chcp 65001 >nul
cd /d "%~dp0"
call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.74.ids.json
pause
