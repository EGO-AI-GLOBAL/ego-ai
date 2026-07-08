@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Android — download AAB + teste FECHADO manual

echo.
echo ============================================================
echo   ANDROID — SEMPRE MANUAL NO TESTE FECHADO
echo   (EAS nao submete mais para Play automaticamente)
echo ============================================================
echo.

for /f "tokens=2 delims=:" %%V in ('findstr /C:"version:" app\app.config.ts') do set VER=%%V
set VER=%VER:"=%
set VER=%VER:,=%
set VER=%VER: =%

if not exist "builds-%VER%.ids.json" (
  echo ERRO: falta builds-%VER%.ids.json — corra GERAR-%VER%.bat primeiro.
  pause
  exit /b 1
)

call _ego_run_python.bat scripts\wait_and_submit_eas.py android-manual --ids-file builds-%VER%.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo Abrindo Play Console — teste FECHADO...
start "" "https://play.google.com/console"
start "" notepad "%~dp0marketing\NOTAS-%VER%-PLAY.txt"
pause
