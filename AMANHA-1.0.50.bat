@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI 1.0.50 — 100%% AUTOMÁTICO

echo.
echo ============================================================
echo   1.0.50 — push + testes + EAS + submit (tudo incluido)
echo ============================================================
echo.
echo Inclui: recuperar senha, avatares escuta, sessao persistente
echo.

python scripts\release_auto.py --version 1.0.50
if errorlevel 1 (
  echo.
  echo FALHOU — ver mensagem acima.
  pause
  exit /b 1
)

echo.
start "" notepad "%~dp0RAILWAY-VARS-1.0.50.txt"
start "" notepad "%~dp0RELEASE-1.0.50-DONE.txt"
start "" notepad "%~dp0supabase\SUPABASE-REDIRECT-RESET-SENHA.txt"
pause
