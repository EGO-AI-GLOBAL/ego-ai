@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — REEL AGENDA (fotos que ja existem)

echo.
echo Teste com fotos antigas (agenda dele) — enquanto nao manda fotos 1.0.42
echo.

python scripts\generate_reel_entrega.py --config marketing\REEL-ENTREGA-AGENDA.json
if errorlevel 1 pause & exit /b 1

start "" "%CD%\marketing\videos\app-real\ego-ai-agenda-retencao-reels.mp4"
start "" notepad "%CD%\marketing\POST-REEL-AGENDA.txt"
pause
