@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.43 — iOS 30 + Android 80

echo.
echo ============================================================
echo   EGO-AI 1.0.43 — EGO de Bolso Fase 2 + fixes agenda
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.43.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-E-SUBMETER-1.0.43.bat
pause
