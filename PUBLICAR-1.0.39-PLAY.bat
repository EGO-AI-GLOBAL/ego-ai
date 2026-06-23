@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Publicar Android 1.0.39 code 73



echo Play teste fechado — 1.0.39 (versionCode 73)

echo 1. Expo — baixar .aab build 73

echo 2. Play Console — teste fechado — nova versao

echo.

start "" notepad "%CD%\marketing\RELEASE-1.0.39.txt"

start "" notepad "%CD%\marketing\NOTAS-1.0.39-PLAY.txt"

pause
