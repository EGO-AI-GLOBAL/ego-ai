@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Verificar sync 4 agentes — 1.0.49

echo.
echo ============================================================
echo   SYNC 1.0.49 — todos os agentes PRONTO?
echo ============================================================
echo.

findstr /C:"⏳" SYNC-AGENTES-1.0.49.txt SYNC-AGENTES-MONSTRINHOS-1.0.49.txt SYNC-AGENTES-BOLSO-1.0.49.txt SYNC-AGENTES-API-1.0.49.txt 2>nul
if not errorlevel 1 (
  echo.
  echo AVISO: ainda ha agente com ⏳ nos ficheiros SYNC acima.
  pause
  exit /b 1
)

python scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 (
  echo.
  echo FALHOU — commit+push ou stash antes de GERAR.
  pause
  exit /b 1
)

echo.
echo OK — pode GERAR-1.0.49.bat
pause
