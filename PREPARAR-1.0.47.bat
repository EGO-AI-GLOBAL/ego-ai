@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Preparar 1.0.47 — testes (SEM build)

echo.
echo ============================================================
echo   PREPARAR 1.0.47 — regression + smoke + sync-check
echo   NAO gera build EAS (isso e GERAR-1.0.47.bat)
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
echo   TUDO PRONTO para build — quando quiser:
echo   GERAR-1.0.47.bat  depois  AGUARDAR-E-SUBMETER-1.0.47.bat
echo ============================================================
pause
