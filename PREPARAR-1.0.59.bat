@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Preparar 1.0.59 — Monstrinhos Fase 7+8

echo.
echo ============================================================
echo   PREPARAR 1.0.59 — loja 34 itens + missões variadas
echo ============================================================
echo.

python scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo OK — quando Release der verde: GERAR-1.0.59.bat
pause
