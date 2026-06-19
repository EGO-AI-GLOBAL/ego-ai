@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.33 — iOS 16 + Android 65

echo.
echo ============================================================
echo   EGO-AI 1.0.33 — Entre Nos + Desabafo
echo ============================================================
echo.
echo ANTES:
echo   1. Cole supabase\COLE-1.0.33-ENTRE-NOS.sql no Supabase
echo   2. git push Railway (API)
echo   3. marketing\RELEASE-1.0.33.txt
echo.

python scripts\regression_guard.py
if errorlevel 1 (
  echo REGRESSION GUARD falhou — corrija antes do build.
  pause
  exit /b 1
)
python scripts\smoke_test_api.py
if errorlevel 1 (
  echo SMOKE TEST falhou — verifique API Railway.
  pause
  exit /b 1
)

cd app
set EAS_BUILD_NO_EXPO_GO_WARNING=true

echo [1/2] iOS 1.0.33 build 16...
call npx eas-cli build --platform ios --profile production --non-interactive

echo.
echo [2/2] Android 1.0.33 code 65...
call npx eas-cli build --platform android --profile production --non-interactive

echo.
echo Proximo: SUBMIT-IOS-1.0.33.bat
echo          PUBLICAR-1.0.33-PLAY.bat
echo          VALIDAR-1.0.33.bat
pause
