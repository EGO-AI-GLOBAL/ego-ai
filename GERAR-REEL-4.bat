@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — REEL 4 Agenda (novo hook VIU)

echo.
echo Reel 4 — hook "Chega de viu" · ~9s · zoom · site egoai.com.br
echo.

python scripts\generate_reel_entrega.py --config marketing\REEL-ENTREGA-4-AGENDA.json
if errorlevel 1 pause & exit /b 1

start "" "%CD%\marketing\videos\app-real\ego-ai-agenda-reel4-reels.mp4"
start "" notepad "%CD%\marketing\POST-REEL-4.txt"
pause
