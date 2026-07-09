@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar 1.0.84 — iOS auto, Android manual

echo iOS: submit automatico para App Store Connect
echo Android: NAO sobe sozinho — nem teste fechado nem interno
echo Android: VOCE decide quando — SUBIR-ANDROID-FECHADO-MANUAL.bat
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.84.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo iOS submetido. Connect: 1.0.84 + build 86 + NOTAS-1.0.84-APP-STORE.txt
echo Android: SUBIR-ANDROID-FECHADO-MANUAL.bat quando build 128 terminar
pause
