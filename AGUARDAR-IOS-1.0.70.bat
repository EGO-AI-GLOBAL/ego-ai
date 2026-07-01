@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar 1.0.70 + TestFlight (só iOS)

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.70.ids.json --ios-only

pause
