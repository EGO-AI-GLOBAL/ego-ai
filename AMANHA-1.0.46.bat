@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Amanha — build 1.0.46

echo.
echo ============================================================
echo   AMANHA: so falta o BUILD EAS (API ja esta no ar)
echo ============================================================
echo.
echo   [OK] Railway: api_build 2026-06-24-1.0.46-invite-growth
echo   [OK] regression_guard + smoke_test_api
echo   [OK] Git main atualizado (1.0.46)
echo.
echo   AMANHA:
echo   1) eas login se precisar (5-eas-login.bat)
echo   2) GERAR-1.0.46.bat
echo   3) AGUARDAR-E-SUBMETER-1.0.46.bat
echo.
echo   DEPOIS de publicar nas lojas (Railway):
echo      EGO_LATEST_APP_VERSION=1.0.46
echo      EGO_LATEST_ANDROID_VERSION_CODE=84
echo.
start "" notepad "%~dp0marketing\VALIDAR-1.0.46.txt"
pause
