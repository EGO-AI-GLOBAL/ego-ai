@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar iOS 1.0.87 — submit App Store

echo iOS: submit automatico App Store Connect (1.0.87 / build 89)
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.87.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo iOS submetido. Connect: versao 1.0.87 + build 89
echo Clique a clique: marketing\APPLE-1.0.87-CLIQUE-A-CLIQUE.txt
echo Notas: marketing\NOTAS-1.0.87-APP-STORE.txt
pause
