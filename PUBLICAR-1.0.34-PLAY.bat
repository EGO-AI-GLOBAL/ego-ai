@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar Android 1.0.34 code 66

echo Play teste fechado — 1.0.34 (versionCode 66)
echo 1. Expo — baixar .aab build 66
echo 2. Play Console — teste fechado — nova versao
echo.
start "" notepad "%CD%\marketing\RELEASE-1.0.34.txt"
pause
