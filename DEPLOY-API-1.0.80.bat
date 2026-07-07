@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API 1.0.80

echo.
echo ============================================================
echo   API 1.0.80 — agenda livre + audio 1x + PAUSA copy
echo ============================================================
echo.

call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1

call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 pause & exit /b 1

echo Railway redeploy automatico apos git push.
echo Cole vars: RAILWAY-VARS-1.0.80.txt
start "" notepad "%~dp0RAILWAY-VARS-1.0.80.txt"
start "" "https://railway.app"

pause
