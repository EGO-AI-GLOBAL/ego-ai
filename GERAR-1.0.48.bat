@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.48 — iOS 35 + Android 86

echo.
echo ============================================================
echo   EGO-AI 1.0.48 — build conjunto (todos os agentes)
echo   Monstrinhos F6 + EGO Bolso + Seguranca/API
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.48.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-E-SUBMETER-1.0.48.bat
pause
