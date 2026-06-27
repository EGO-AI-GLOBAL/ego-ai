@echo off
cd /d "%~dp0"
echo === EGO-AI — Verificacao de seguranca ===
echo.
echo [1/2] Monitor producao + codigo...
python scripts\security_monitor.py
set RC=%ERRORLEVEL%
echo.
echo [2/2] Check completo pre-deploy...
python scripts\security_production_check.py
if %ERRORLEVEL% neq 0 set RC=1
echo.
if %RC% neq 0 (
  echo FALHOU — corrija antes de deploy/build.
) else (
  echo OK — pode deploy/build apos SQL RLS + vars Railway.
)
pause
exit /b %RC%
