@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Publicar Android 1.0.38 code 72



echo Play teste fechado — 1.0.38 (versionCode 72)

echo 1. Expo — baixar .aab build 72

echo 2. Play Console — teste fechado — nova versao

echo.

start "" notepad "%CD%\marketing\RELEASE-1.0.38.txt"

start "" notepad "%CD%\marketing\NOTAS-1.0.38-PLAY.txt"

pause
