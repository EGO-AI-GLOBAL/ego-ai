@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Amanhã — build 1.0.47

echo.
echo ============================================================
echo   AMANHÃ: BUILD 1.0.47 (API já no ar — sem build hoje)
echo ============================================================
echo.
echo   [OK] API: missões 5/dia + convite 10/20/30 + validação 1000
echo.
echo   SUBIR BUILD 1.0.47 (quando quiser):
echo   1) eas login se precisar (5-eas-login.bat)
echo   2) SUBIR-BUILD-1.0.47.bat
echo   3) AGUARDAR-E-SUBMETER-1.0.47.bat
echo.
echo   iOS teste EXTERNO (se 1.0.46 bloqueou): SUBMIT-IOS-EXTERN-1.0.46.bat
echo.
echo   DEPOIS de publicar 1.0.47 (Railway):
echo      EGO_LATEST_APP_VERSION=1.0.47
echo      EGO_LATEST_ANDROID_VERSION_CODE=85
echo.
start "" notepad "%~dp0marketing\VALIDAR-1.0.47.txt"
pause
