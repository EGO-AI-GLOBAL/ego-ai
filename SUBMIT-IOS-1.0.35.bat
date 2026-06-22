@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.35 build 18

echo Submit TestFlight 1.0.35 build 18
call npx eas-cli submit --platform ios --latest --non-interactive
pause
