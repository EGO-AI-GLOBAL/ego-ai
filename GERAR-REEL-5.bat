@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — REEL 5 (POV 23h — teste novo)

echo.
echo Reel 5 — POV desabafo 23h · hook NOVO · nao repete Reel 3 nem 4
echo.

python scripts\generate_reel_entrega.py --config marketing\REEL-ENTREGA-5-AGENDA.json
if errorlevel 1 pause & exit /b 1

start "" "%CD%\marketing\videos\app-real\ego-ai-agenda-reel5-reels.mp4"
start "" notepad "%CD%\marketing\POST-REEL-5.txt"
pause
