@echo off
chcp 65001 >nul
cd /d "%~dp0"
title SUBIR BUILD 1.0.47 — um clique

echo.
echo ============================================================
echo   EGO-AI 1.0.47 — pronto para enfileirar build EAS
echo ============================================================
echo.
echo   Inclui:
echo   • EGO de Bolso — habitat animado (Dia 1) + 5 missões/dia
echo   • Habitat animado no EGO de Bolso (Dia 1 v2)
echo   • Monstrinhos Fase 5 visual
echo.
echo   Versão: 1.0.47 | iOS 34 | Android 85
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo   [OK] Testes passaram. A enfileirar iOS + Android...
echo.

python scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.47.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo   Builds na fila. Quando terminar:
echo   AGUARDAR-E-SUBMETER-1.0.47.bat
echo.
start "" notepad "%~dp0marketing\VALIDAR-1.0.47.txt"
pause
