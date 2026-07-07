@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Promover 1.0.80 — teste fechado

echo.
echo ============================================================
echo   ANDROID 1.0.80 (125) — TESTE FECHADO
echo ============================================================
echo.
echo  eas.json track=alpha — EAS submit vai para teste FECHADO.
echo  Link testadores: https://play.google.com/apps/testing/com.egoai.app
echo.
echo  Se AGUARDAR-E-SUBMETER-1.0.80.bat ja correu, nada a fazer.
echo  Senao: FAZ-TUDO-1.0.80.bat ou SUBMIT-ANDROID-FECHADO-1.0.80.bat
echo.
pause
start "" "https://play.google.com/console"
