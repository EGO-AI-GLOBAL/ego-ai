@echo off
REM Abre Railway + ficheiros para colar (freemium lojas)
start "" "https://railway.app/dashboard"
start "" "https://play.google.com/console"
start "" "https://appstoreconnect.apple.com/apps/6780595396/distribution"
start "" "https://ego-ai-production-a2c2.up.railway.app/api/health"
notepad "%~dp0RAILWAY-VARS-1.0.104.txt"
notepad "%~dp0marketing\PLAY-FICHA-FREEMIUM-COLAR-AGORA-28-07.txt"
notepad "%~dp0VOCE-SO-FAZ-FREEMIUM-LOJAS.txt"
echo.
echo Abri Railway, Play, App Store Connect e os ficheiros para colar.
echo Faz: 1) Vars + Redeploy Railway  2) Colar ficha Play  3) Colar iOS
pause
