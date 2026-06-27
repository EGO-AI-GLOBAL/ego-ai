@echo off
cd /d "%~dp0"
echo === EGO-AI — Monitor seguranca automatico ===
python scripts\security_monitor.py
set RC=%ERRORLEVEL%
if %RC% neq 0 (
  echo.
  echo ALERTA — ver marketing\SEGURANCA-STATUS.txt
)
exit /b %RC%
