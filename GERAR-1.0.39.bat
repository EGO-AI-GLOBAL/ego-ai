@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.39 — iOS 24 + Android 73



echo.

echo ============================================================

echo   EGO-AI 1.0.39 — Menu Desafio/Jornada + 500 niveis + WA 2 links

echo ============================================================

echo.

echo ANTES (manual): git push + Railway redeploy + SQL progression caps

echo   supabase\COLE-PROGRESSION-CAPS.sql no Supabase SQL Editor

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



echo [1/2] iOS 1.0.39 build 24...

call eas build --platform ios --profile production --non-interactive



echo.

echo [2/2] Android 1.0.39 code 73...

call eas build --platform android --profile production --non-interactive



echo.

echo Proximo: SUBMIT-IOS-1.0.39.bat + PUBLICAR-1.0.39-PLAY.bat (criar a partir dos 1.0.38)

pause
