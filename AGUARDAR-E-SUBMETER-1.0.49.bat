@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI 1.0.49 — aguardar iOS+Android e submeter

echo.
python scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.49.ids.json
if errorlevel 1 ( pause & exit /b 1 )

start "" notepad "%~dp0marketing\NOTAS-1.0.49-PLAY.txt"
pause
