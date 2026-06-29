@echo off
chcp 65001 >nul
cd /d "%~dp0app"
title Submit Android 1.0.57 — Play (build dc04b183)

echo.
echo ============================================================
echo   EGO-AI 1.0.57 — submit Android (versionCode 97)
echo ============================================================
echo.
echo Requer: app\play-store-service-account.json
echo Build ID: dc04b183-2f18-45e2-bf64-8e5251f2150d
echo.

if not exist "play-store-service-account.json" (
  echo ERRO: Copie o JSON da Google Play para:
  echo   app\play-store-service-account.json
  echo.
  pause
  exit /b 1
)

set NODE_TLS_REJECT_UNAUTHORIZED=0
call npx eas submit --platform android --id dc04b183-2f18-45e2-bf64-8e5251f2150d --non-interactive
if errorlevel 1 pause & exit /b 1

echo.
echo OK — confira Play Console ^> teste fechado ^> 1.0.57
pause
