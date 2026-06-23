@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Publicar Android 1.0.40 code 75



echo Play teste fechado — 1.0.40 (versionCode 75)

echo 1. Expo — baixar .aab build 75

echo 2. Play Console — teste fechado — nova versao

echo.

start "" notepad "%CD%\marketing\RELEASE-1.0.40.txt"

start "" notepad "%CD%\marketing\NOTAS-1.0.40-PLAY.txt"

pause
