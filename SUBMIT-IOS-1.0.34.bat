@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.34 build 17

echo Submit TestFlight 1.0.34 build 17
call npx eas-cli submit --platform ios --latest --non-interactive
pause
