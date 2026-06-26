@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.48 — testes (SEM build)

echo.
echo ============================================================
echo   PREPARAR 1.0.48 — regression + smoke + sync-check
echo   NAO gera build EAS (isso e GERAR-1.0.48.bat)
echo   AGUARDE todos os agentes terminarem antes do GERAR
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo ============================================================
echo   TUDO PRONTO para build — quando TODOS agentes disserem OK:
echo   GERAR-1.0.48.bat  depois  AGUARDAR-E-SUBMETER-1.0.48.bat
echo ============================================================
pause
