@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Aguardar 1.0.83 — iOS only (Jardim da Gentileza)



echo.

echo ============================================================

echo   1.0.83 — iOS build 85 · sem Android

echo ============================================================

echo.

echo Connect: marketing/NOTAS-1.0.83-APP-STORE.txt

echo.



call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ios-only --ids-file builds-1.0.83.ids.json

if errorlevel 1 pause & exit /b 1



echo.

echo OK — anexar build 85 na versao 1.0.83 no App Store Connect.

pause

