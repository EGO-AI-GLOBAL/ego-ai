@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI 1.0.50 — AUTOMÁTICO (amanhã)

echo.
echo ============================================================
echo   1.0.50 AUTOMÁTICO — testes + EAS + submeter lojas
echo ============================================================
echo.
echo Antes de correr: Supabase Redirect URLs (ver VOCE-SO-FAZ-ISTO-1.0.50.txt)
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo --- Enfileirando iOS 38 + Android 89 ---
python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.50.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo --- Aguardando builds e submetendo TestFlight + Play ---
python scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.50.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo ============================================================
echo   CONCLUÍDO — ver NOTAS-1.0.50-PLAY.txt para Railway
echo ============================================================
start "" notepad "%~dp0marketing\NOTAS-1.0.50-PLAY.txt"
start "" notepad "%~dp0VOCE-SO-FAZ-ISTO-1.0.50.txt"
pause
