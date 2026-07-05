@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aguardar e submeter 1.0.78 — iOS + Android

if not exist "builds-1.0.78.ids.json" (
  echo.
  echo  FALTA O PASSO 1 — ainda nao enfileirou os builds.
  echo  Corra primeiro:  GERAR-1.0.78.bat
  echo  Depois volte aqui: AGUARDAR-E-SUBMETER-1.0.78.bat
  echo.
  pause
  exit /b 1
)

call _ego_run_python.bat scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.78.ids.json
pause
