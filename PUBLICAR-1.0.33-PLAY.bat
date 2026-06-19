@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar Android 1.0.33 code 65

echo Play teste fechado — 1.0.33 (versionCode 65)
echo.
echo 1. Play Console - enviar AAB build 65
echo 2. Railway EGO_LATEST_APP_VERSION=1.0.33
echo 3. Railway EGO_LATEST_ANDROID_VERSION_CODE=65
echo.
start "" notepad "%CD%\marketing\RELEASE-1.0.33.txt"
pause
