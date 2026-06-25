@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submeter iOS 1.0.46 — só TestFlight (limite externo)

echo.
echo Build iOS 1.0.46: d319088c-8af4-443b-9503-6ef044b9f286
echo Use AMANHA se Apple bloqueou teste externo (2/dia).
echo.
pause

set NODE_TLS_REJECT_UNAUTHORIZED=0
set EAS_BUILD_NO_EXPO_GO_WARNING=true
call eas submit --platform ios --id d319088c-8af4-443b-9503-6ef044b9f286 --profile production --non-interactive
pause
