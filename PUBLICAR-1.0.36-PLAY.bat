@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar Android 1.0.36 code 68

echo Play teste fechado — 1.0.36 (versionCode 68)
echo 1. Expo — baixar .aab build 68
echo 2. Play Console — teste fechado — nova versao
echo.
start "" notepad "%CD%\marketing\RELEASE-1.0.36.txt"
start "" notepad "%CD%\marketing\NOTAS-1.0.36-PLAY.txt"
pause
