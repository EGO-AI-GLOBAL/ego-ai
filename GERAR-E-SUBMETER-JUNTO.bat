@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — GERAR builds juntos (iOS + Android)

echo.
echo ============================================================
echo   REGRA DOIS AGENTES: esperar o outro no Git, depois build
echo   NAO use SUBMIT-IOS nem PUBLICAR-PLAY separados
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py queue
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Builds enfileirados. Quando quiser subir as LOJAS:
echo   AGUARDAR-E-SUBMETER.bat
pause
