@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API 1.0.74

echo.
echo Railway — vars em RAILWAY-VARS-1.0.74.txt
echo Obrigatorio ANTES do build 1.0.74 (realtime + TTS inline + journal-note).
echo.
type RAILWAY-VARS-1.0.74.txt
start "" notepad "%~dp0RAILWAY-VARS-1.0.74.txt"
start "" "https://railway.app"
call _ego_run_python.bat scripts\smoke_test_api.py
pause
