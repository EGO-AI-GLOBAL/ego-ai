@echo off

chcp 65001 >nul

cd /d "%~dp0"

title EGO-AI 1.0.51 — 100%% AUTOMÁTICO



echo.

echo ============================================================

echo   1.0.51 — push + testes + EAS + submit (tudo incluido)

echo ============================================================

echo.

echo Inclui: 12 personalidades, avatar do dia, memória leve, streak chat

echo.



python scripts\release_auto.py --version 1.0.51

if errorlevel 1 (

  echo.

  echo FALHOU — ver mensagem acima.

  pause

  exit /b 1

)



echo.

start "" notepad "%~dp0RAILWAY-VARS-1.0.51.txt"

start "" notepad "%~dp0marketing\NOTAS-1.0.51-PLAY.txt"

pause
