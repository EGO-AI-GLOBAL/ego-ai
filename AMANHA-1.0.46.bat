@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Amanha — build 1.0.46

echo.
echo ============================================================
echo   AMANHA: EGO-AI 1.0.46 (API + app juntos)
echo ============================================================
echo.
echo   1) Railway ja redeployou? Confira /health:
echo      api_build = 2026-06-24-1.0.46-invite-growth
echo.
echo   2) Duplo-clique: GERAR-1.0.46.bat
echo      (valida + enfileira iOS 33 e Android 84)
echo.
echo   3) Quando builds terminarem: AGUARDAR-E-SUBMETER-1.0.46.bat
echo.
echo   4) Railway (apos publicar nas lojas):
echo      EGO_LATEST_APP_VERSION=1.0.46
echo      EGO_LATEST_ANDROID_VERSION_CODE=84
echo.
start "" notepad "%~dp0marketing\VALIDAR-1.0.46.txt"
pause
