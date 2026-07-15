@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar 1.0.89 — iOS auto, Android manual

echo iOS: submit automatico para App Store Connect
echo Android: NAO sobe sozinho — fluxo manual fechado quando AAB terminar
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.89.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo iOS submetido. Connect: 1.0.89 + build 91
echo Android: versionCode 133 — subir manual quando o build EAS terminar
pause
