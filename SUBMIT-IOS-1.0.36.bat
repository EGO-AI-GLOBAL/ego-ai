@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.36 build 19

echo Submit TestFlight 1.0.36 build 19
set NODE_TLS_REJECT_UNAUTHORIZED=0
call eas submit --platform ios --latest --non-interactive
pause
