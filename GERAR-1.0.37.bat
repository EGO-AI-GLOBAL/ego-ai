@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Gerar 1.0.37 — iOS 22 + Android 71



echo.

echo ============================================================

echo   EGO-AI 1.0.37 — fix telefone no cadastro (loop iOS)

echo ============================================================

echo.

echo ANTES: git push main + Railway EGO_LATEST_APP_VERSION=1.0.37

echo        EGO_LATEST_ANDROID_VERSION_CODE=71

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



echo [1/2] iOS 1.0.37 build 22...

call eas build --platform ios --profile production --non-interactive



echo.

echo [2/2] Android 1.0.37 code 71...

call eas build --platform android --profile production --non-interactive



echo.

echo Proximo: SUBMIT-IOS-1.0.37.bat

pause

