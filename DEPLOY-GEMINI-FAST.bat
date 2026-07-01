@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DEPLOY Gemini Fast + Edge TTS (sem Realtime, sem build)

echo.
echo ============================================================
echo   VOZ RAPIDA — Gemini Flash + Edge TTS (defer TTS)
echo   Nao precisa build novo — so redeploy Railway
echo ============================================================
echo.
echo  Texto no chat: ~5-8 s  ^|  Avatar fala: ~7-11 s
echo.

call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo --- API AGORA ---
call _ego_run_python.bat -c "import urllib.request,json,ssl; ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; r=urllib.request.urlopen(urllib.request.Request('https://ego-ai-production-a2c2.up.railway.app/api/v1/health'),context=ctx,timeout=20); d=json.loads(r.read()); print('api_build:',d.get('api_build')); print('voice:',d.get('voice')); print('realtime:',d.get('realtime'))"

echo.
echo MANUAL (3 passos):
echo   1. GitHub main ja tem o codigo — Railway servico API
echo   2. Variables: copiar RAILWAY-VARS-GEMINI-FAST.txt
echo   3. Deployments -^> Redeploy
echo.
start "" notepad "%~dp0RAILWAY-VARS-GEMINI-FAST.txt"
start "" "https://railway.app"
pause

echo.
echo --- DEPOIS DO REDEPLOY ---
call _ego_run_python.bat -c "import urllib.request,json,ssl; ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; r=urllib.request.urlopen(urllib.request.Request('https://ego-ai-production-a2c2.up.railway.app/api/v1/health'),context=ctx,timeout=20); d=json.loads(r.read()); b=str(d.get('api_build','')); v=d.get('voice') or {}; rt=(d.get('realtime') or {}).get('available'); print('api_build:',b); print('fast_path:',v.get('fast_path')); print('defer_tts:',v.get('defer_tts_on_voice')); print('realtime:',rt); print('OK' if 'GEMINI-FAST' in b and v.get('fast_path') and not rt else 'AINDA NAO — redeploy de novo')"
pause
