@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — Reel de hoje (SITE)

echo.
echo  POST DIARIO — link sempre: https://egoai.com.br
echo  REEL 4 — fotos ajustadas + legendas
echo.

set "MP4=%CD%\marketing\videos\app-real\ego-ai-agenda-reel4-reels.mp4"
set "GUIA=%CD%\marketing\POST-REEL-4.txt"

if not exist "%MP4%" (
  echo ERRO: MP4 nao encontrado. Rode GERAR-REEL-4.bat
  pause
  exit /b 1
)

start "" "%MP4%"
start "" notepad "%GUIA%"

echo.
echo  1) Postar esse MP4 no Instagram Reels
echo  2) Legenda + link: marketing\POST-DIARIO-SITE.txt
echo  3) Comentario fixado: https://egoai.com.br
echo  4) Turbinar = visitantes do SITE (nao perfil)
echo.
pause
