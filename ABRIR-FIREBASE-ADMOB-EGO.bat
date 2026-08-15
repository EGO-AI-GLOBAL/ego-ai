@echo off
chcp 65001 >nul
title EGO-AI — Firebase + AdMob units
cd /d "%~dp0"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"

echo.
echo A abrir Firebase + AdMob + checklist...
echo.

start "" "%CHROME%" "https://console.firebase.google.com"
start "" "%CHROME%" "https://admob.google.com"
start "" notepad "%~dp0VOCE-SO-FAZ-FIREBASE-ADMOB-EGO.txt"

pause
