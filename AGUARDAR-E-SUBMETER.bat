@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — aguardar iOS+Android e submeter UMA vez

echo.
echo ============================================================
echo   Espera iOS + Android FINISHED
echo   Submete TestFlight + Play JUNTOS (uma vez so)
echo ============================================================
echo.

python scripts\wait_and_submit_eas.py wait-submit
if errorlevel 1 ( pause & exit /b 1 )

for /f "tokens=2 delims=:" %%V in ('findstr /C:"version:" app\app.config.ts') do set VER=%%V
set VER=%VER:"=%
set VER=%VER:,=%
set VER=%VER: =%

echo.
echo Abrir notas release...
if exist "marketing\RELEASE-%VER%.txt" start "" notepad "%~dp0marketing\RELEASE-%VER%.txt"
if exist "marketing\NOTAS-%VER%-PLAY.txt" start "" notepad "%~dp0marketing\NOTAS-%VER%-PLAY.txt"
pause
