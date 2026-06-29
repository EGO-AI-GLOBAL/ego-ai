@echo off

chcp 65001 >nul

cd /d "%~dp0"

title EGO-AI 1.0.52 HOTFIX — 100%% AUTOMATICO

echo.
echo ============================================================
echo   1.0.52 HOTFIX — push + testes + EAS + submit
echo   Crash avatar + recuperar senha
echo ============================================================
echo.

python scripts\release_auto.py --version 1.0.52
if errorlevel 1 (
  echo.
  echo FALHOU — ver mensagem acima.
  pause
  exit /b 1
)

echo.
start "" notepad "%~dp0RAILWAY-VARS-1.0.52.txt"
start "" notepad "%~dp0VOCE-SO-FAZ-ISTO-1.0.52.txt"
start "" notepad "%~dp0marketing\NOTAS-1.0.52-PLAY.txt"
pause
