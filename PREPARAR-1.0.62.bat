@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Preparar 1.0.62 — voz Android + Bolso + Monstrinhos

echo.
echo ============================================================
echo   PREPARAR 1.0.62 — pacote completo (voz mic+seta, widgets)
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
echo OK — utilizador testa TESTAR-VOZ-USB-GRATIS.bat no Android
echo Depois (4x SYNC PRONTO): GERAR-1.0.62.bat
pause
