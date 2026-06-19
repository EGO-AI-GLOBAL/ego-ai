@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API 1.0.33

echo.
echo DEPLOY 1.0.33 — Railway (API)
echo.
python scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1
python scripts\smoke_test_api.py
echo.
echo Se OK local, faca git add/commit/push para Railway redeployar.
echo Depois confirme /health api_build=2026-06-17-1.0.33-entre-nos
echo.
echo Railway variables:
echo   EGO_LATEST_APP_VERSION=1.0.33
echo   EGO_LATEST_ANDROID_VERSION_CODE=65
echo.
pause
