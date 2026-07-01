@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DEPLOY VOZ URGENTE — Railway (SEM build app)

echo.
echo ============================================================
echo   VOZ LENTA — CORRIGE NA API, NAO NO BUILD DO APP
echo ============================================================
echo.
echo  Build 1.0.74 ja instalado BASTA se a API redeployar.
echo  Confirmar DEPOIS do redeploy:
echo    api_build = 2026-07-02-VOZ-URGENTE
echo    voice.fast_path = true
echo.

call _ego_run_python.bat -c "import urllib.request,json; r=urllib.request.urlopen('https://ego-ai-production-a2c2.up.railway.app/api/v1/health',timeout=20); d=json.loads(r.read()); print('AGORA api_build:',d.get('api_build')); print('voice:',d.get('voice'))"

echo.
echo 1. GitHub ja tem o codigo — Railway: servico API
echo 2. Deployments -^> Redeploy (ou ligar repo main auto-deploy)
echo 3. Variables (copiar RAILWAY-VARS-1.0.75-VOZ.txt):
echo    EGO_VOICE_FAST=1
echo.
start "" notepad "%~dp0RAILWAY-VARS-1.0.75-VOZ.txt"
start "" "https://railway.app"
echo.
pause

echo.
call _ego_run_python.bat -c "import urllib.request,json; r=urllib.request.urlopen('https://ego-ai-production-a2c2.up.railway.app/api/v1/health',timeout=20); d=json.loads(r.read()); b=d.get('api_build',''); print('DEPOIS api_build:',b); print('OK' if 'VOZ-URGENTE' in b else 'AINDA NAO — redeploy de novo')"

pause
