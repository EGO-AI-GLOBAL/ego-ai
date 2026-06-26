@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — REEL PRONTO (fotos + voz + legenda)

echo.
echo REEL ENTREGA — coloque 5 fotos em marketing\CAPCUT-FOTOS-ENTREGA\
echo Veja LEIA-ME.txt na pasta. Demora 3 a 5 minutos.
echo.

python scripts\generate_reel_entrega.py
if errorlevel 1 (
  echo.
  echo Se faltar ffmpeg: winget install ffmpeg
  echo Se faltar: pip install pillow edge-tts
  start "" explorer "%CD%\marketing\CAPCUT-FOTOS-ENTREGA"
  pause
  exit /b 1
)

echo.
echo Abrindo video e legenda do post...
start "" "%CD%\marketing\videos\app-real\ego-ai-1.0.42-retencao-reels.mp4"
explorer /select,"%CD%\marketing\videos\app-real\ego-ai-1.0.42-retencao-reels.mp4"
start "" notepad "%CD%\marketing\POST-REEL-ENTREGA.txt"
pause
