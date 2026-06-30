@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar e submeter 1.0.69 (iOS + Android)

echo Use AGUARDAR-IOS-1.0.69.bat primeiro se ainda nao testou voz no iPhone.
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.69.ids.json

pause
