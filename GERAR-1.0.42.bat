@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.42 — iOS 28 + Android 77

echo.
echo ============================================================
echo   EGO-AI 1.0.42 — Monstrinhos Finch (missões + sementes)
echo ============================================================
echo.
echo ANTES: DEPLOY-API-1.0.42.bat
echo   Railway: EGO_LATEST_APP_VERSION=1.0.42  code 77
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

cd app
set EAS_BUILD_NO_EXPO_GO_WARNING=true
set NODE_TLS_REJECT_UNAUTHORIZED=0

echo [1/2] iOS 1.0.42 build 28...
call eas build --platform ios --profile production --non-interactive

echo.
echo [2/2] Android 1.0.42 code 77...
call eas build --platform android --profile production --non-interactive

echo.
echo Proximo: SUBMIT iOS + PUBLICAR Play (mesmo fluxo 1.0.41)
pause
