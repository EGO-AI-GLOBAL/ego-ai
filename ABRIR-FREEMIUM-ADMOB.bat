@echo off
chcp 65001 >nul
title EGO-AI — Freemium + AdMob (links manuais)
cd /d "%~dp0"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

echo.
echo A abrir AdMob, Railway, EAS, Play e App Store no Chrome...
echo Checklist: VOCE-SO-FAZ-FREEMIUM-ADMOB.txt
echo.

start "" "%CHROME%" "https://admob.google.com"
start "" "%CHROME%" "https://railway.app/dashboard"
start "" "%CHROME%" "https://expo.dev/accounts/iuryfreiras/projects/ego-ai/environment-variables"
start "" "%CHROME%" "https://play.google.com/console"
start "" "%CHROME%" "https://appstoreconnect.apple.com/apps/6780595396"
start "" notepad "%~dp0VOCE-SO-FAZ-FREEMIUM-ADMOB.txt"

pause
