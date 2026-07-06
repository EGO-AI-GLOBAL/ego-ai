@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Amanha — build 1.0.80

echo.
echo ============================================================
echo   AMANHA — EGO-AI 1.0.80 (jardim humor primeiro)
echo ============================================================
echo.
echo  1. git pull
echo  2. PREPARAR-1.0.80.bat
echo  3. GERAR-1.0.80.bat        (demora ~15-30 min)
echo  4. AGUARDAR-E-SUBMETER-1.0.80.bat
echo  5. Play: NOTAS em marketing\NOTAS-1.0.80-PLAY.txt
echo  6. iOS: NOTAS em marketing\NOTAS-1.0.80-APP-STORE.txt
echo.
echo  NAO precisa deploy Railway (só UI).
echo  PAUSA EGO e IAP ficam como na 1.0.79.
echo.
pause
