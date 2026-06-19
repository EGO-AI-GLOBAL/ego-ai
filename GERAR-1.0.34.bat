@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.34 — iOS 17 + Android 66

echo.
echo ============================================================
echo   EGO-AI 1.0.34 — hotfix agenda compartilhada + Entre Nos
echo ============================================================
echo.
echo ANTES: DEPLOY-API-1.0.34.bat + Railway 1.0.34 / code 66
echo.

python scripts\regression_guard.py
if errorlevel 1 (
  echo REGRESSION GUARD falhou.
  pause
  exit /b 1
)
python scripts\smoke_test_api.py
if errorlevel 1 (
  echo SMOKE TEST falhou.
  pause
  exit /b 1
)

cd app
set EAS_BUILD_NO_EXPO_GO_WARNING=true

echo [1/2] iOS 1.0.34 build 17...
call npx eas-cli build --platform ios --profile production --non-interactive

echo.
echo [2/2] Android 1.0.34 code 66...
call npx eas-cli build --platform android --profile production --non-interactive

echo.
echo Proximo: SUBMIT-IOS-1.0.34.bat + PUBLICAR-1.0.34-PLAY.bat
pause
