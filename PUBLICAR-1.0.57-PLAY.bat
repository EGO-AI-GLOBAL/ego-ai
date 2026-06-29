@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar 1.0.57 — TestFlight + Play

echo.
echo ============================================================
echo   EGO-AI 1.0.57 — publicar testadores
echo ============================================================
echo.
echo iOS: ja submetido ao TestFlight (build 45)
echo      TestFlight -^> instalar 1.0.57
echo.
echo Android: correr SUBMIT-ANDROID-1.0.57.bat (precisa JSON Play)
echo.
echo Railway: colar variaveis de RAILWAY-VARS-1.0.57.txt + Redeploy
echo.

start "" notepad "%CD%\RAILWAY-VARS-1.0.57.txt"
start "" notepad "%CD%\marketing\MENSAGEM-TESTADORES-1.0.57.txt"
start "" notepad "%CD%\marketing\NOTAS-1.0.57-PLAY.txt"
start "" "https://testflight.apple.com/join/eNDKdFWF"
start "" "https://railway.app"

pause
