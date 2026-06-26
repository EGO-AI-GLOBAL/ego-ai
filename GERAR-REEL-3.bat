@echo off

chcp 65001 >nul

cd /d "%~dp0"

title EGO-AI — REEL 3 Agenda (~10s)



echo.

echo Reel 3 — 4 cenas, ~10 segundos, mesmo estilo do Agenda vencedor

echo.



python scripts\generate_reel_entrega.py --config marketing\REEL-ENTREGA-3-AGENDA.json

if errorlevel 1 pause & exit /b 1



start "" "%CD%\marketing\videos\app-real\ego-ai-agenda-reel3-reels.mp4"

start "" notepad "%CD%\marketing\POST-REEL-3.txt"

pause

