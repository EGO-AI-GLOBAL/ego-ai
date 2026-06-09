@echo off
setlocal
chcp 65001 >nul
title EGO-AI - Verificar antes de deploy
cd /d "%~dp0"
set EXITCODE=0

echo.
echo === EGO-AI: verificacao antes de deploy / build Play ===
echo Pasta: %CD%
echo.

if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

"%PY%" --version >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python nao encontrado. Instale Python ou crie .venv na pasta do projeto.
  set EXITCODE=1
  goto :end
)

echo [1/2] regression_guard.py
"%PY%" scripts\regression_guard.py
if errorlevel 1 set EXITCODE=1

echo.
echo [2/2] smoke_test_api.py
"%PY%" scripts\smoke_test_api.py
if errorlevel 1 set EXITCODE=1

goto :end

:end
echo.
if %EXITCODE% equ 0 (
  echo OK — pode fazer deploy Railway ou build EAS.
  echo Lembrete: EGO_MAINTENANCE=1 deve estar APAGADO no Railway.
) else (
  echo FALHOU — corrija ou reverta antes de publicar.
  echo Se o erro for SSL/rede no PC, o codigo local pode estar OK mesmo assim.
)
echo.
pause
exit /b %EXITCODE%
