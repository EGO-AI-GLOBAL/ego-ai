@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.33 build 16

echo Submit TestFlight 1.0.33 build 16
echo Validar depois: VALIDAR-1.0.33.bat
echo.
call npx eas-cli submit --platform ios --latest --non-interactive
pause
