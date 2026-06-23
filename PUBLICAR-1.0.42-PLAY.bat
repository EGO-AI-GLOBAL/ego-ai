@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Publicar Android 1.0.42 code 77
echo Play teste fechado — 1.0.42 (versionCode 77)
set EAS_BUILD_NO_EXPO_GO_WARNING=true
set NODE_TLS_REJECT_UNAUTHORIZED=0
call eas submit --platform android --latest --non-interactive
start "" notepad "%~dp0marketing\RELEASE-1.0.42.txt"
start "" notepad "%~dp0marketing\NOTAS-1.0.42-PLAY.txt"
pause
