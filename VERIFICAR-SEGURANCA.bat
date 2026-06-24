@echo off
cd /d "%~dp0"
echo === EGO-AI — Verificacao de seguranca ===
python scripts\security_production_check.py
set RC=%ERRORLEVEL%
echo.
if %RC% neq 0 (
  echo FALHOU — corrija antes de deploy/build.
) else (
  echo OK — pode deploy/build apos SQL RLS + vars Railway.
)
pause
exit /b %RC%
