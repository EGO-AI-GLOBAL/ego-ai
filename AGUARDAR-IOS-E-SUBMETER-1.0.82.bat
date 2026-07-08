@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar iOS 1.0.82

echo iOS: submit automatico para TestFlight / App Store Connect
echo Android: NAO construir nesta release
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.82.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo iOS submetido. Connect: versao 1.0.82 + colar marketing\NOTAS-1.0.82-APP-STORE.txt
pause
