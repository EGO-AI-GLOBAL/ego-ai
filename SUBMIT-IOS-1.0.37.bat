@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.37 build 20

echo Submetendo ultimo build iOS para TestFlight...
set EAS_BUILD_NO_EXPO_GO_WARNING=true
set NODE_TLS_REJECT_UNAUTHORIZED=0
call eas submit --platform ios --latest --non-interactive
pause
