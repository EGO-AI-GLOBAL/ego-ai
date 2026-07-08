@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar 1.0.81 — iOS auto, Android manual

echo iOS: submit automatico para TestFlight
echo Android: VOCE sobe manual no teste fechado (SUBIR-ANDROID-FECHADO-MANUAL.bat)
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.81.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo iOS submetido. Android: corra SUBIR-ANDROID-FECHADO-MANUAL.bat quando quiser.
pause
