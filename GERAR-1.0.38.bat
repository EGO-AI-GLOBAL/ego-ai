@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.38 — iOS 23 + Android 72



echo.

echo ============================================================

echo   EGO-AI 1.0.38 — Desafio Diário + Jornada + trial

echo ============================================================

echo.

echo ANTES (manual): git push + Railway redeploy — ver PASO-A-PASSO-MANUAL-1.0.38.md

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

set NODE_TLS_REJECT_UNAUTHORIZED=0



echo [1/2] iOS 1.0.38 build 23...

call eas build --platform ios --profile production --non-interactive



echo.

echo [2/2] Android 1.0.38 code 72...

call eas build --platform android --profile production --non-interactive



echo.

echo Proximo: SUBMIT-IOS-1.0.38.bat + PUBLICAR-1.0.38-PLAY.bat

pause
