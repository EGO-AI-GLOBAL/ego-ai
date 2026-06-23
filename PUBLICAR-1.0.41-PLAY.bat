@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publicar Android 1.0.41 code 76
echo Play teste fechado — 1.0.41 (versionCode 76)
start "" notepad "%CD%\marketing\RELEASE-1.0.41.txt"
start "" notepad "%CD%\marketing\NOTAS-1.0.41-PLAY.txt"
pause
