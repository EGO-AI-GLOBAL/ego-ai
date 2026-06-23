@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Verificar cadastro duplicado

if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

echo.
echo === EGO-AI: bloqueio e-mail + telefone no cadastro ===
echo.

"%PY%" scripts\regression_guard.py
if errorlevel 1 goto :fail

"%PY%" scripts\smoke_test_signup_duplicate.py
if errorlevel 1 goto :fail

echo.
echo OK — cadastro duplicado funcionando na API.
goto :end

:fail
echo.
echo FALHOU — veja mensagens acima.
pause
exit /b 1

:end
pause
exit /b 0
