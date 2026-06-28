@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Preparar 1.0.51 — testes (SEM build)



echo.

echo ============================================================

echo   PREPARAR 1.0.51 — regression + smoke + sync-check

echo ============================================================

echo.



python scripts\regression_guard.py

if errorlevel 1 ( pause & exit /b 1 )



python scripts\smoke_test_api.py

if errorlevel 1 ( pause & exit /b 1 )



python scripts\wait_and_submit_eas.py sync-check

if errorlevel 1 ( pause & exit /b 1 )



echo.

echo OK — quando quiser: GERAR-1.0.51.bat

pause
