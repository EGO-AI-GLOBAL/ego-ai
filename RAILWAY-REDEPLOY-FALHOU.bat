@echo off
cd /d "%~dp0"
echo === Railway redeploy falhou? ===
echo.
echo A API ANTIGA ainda esta no ar se /health responde.
echo.
python -c "import urllib.request,json; r=urllib.request.urlopen('https://ego-ai-production-a2c2.up.railway.app/api/v1/health',timeout=15); d=json.loads(r.read()); print('ok:',d.get('ok'),'build:',d.get('api_build'))"
echo.
echo Causas mais comuns:
echo   1. GOOGLE_SERVICE_ACCOUNT_JSON mal colado (aspas extra ou JSON cortado)
echo   2. EGO_ENFORCE_HTTPS=1 bloqueava healthcheck (corrigido no codigo - precisa git push)
echo   3. Codigo novo ainda nao foi para o GitHub (git push)
echo.
echo Solucao rapida no Railway:
echo   - Remova GOOGLE_SERVICE_ACCOUNT_JSON temporariamente
echo   - EGO_PLAY_INTEGRITY=0
echo   - EGO_ENFORCE_HTTPS=0
echo   - Redeploy
echo   - Depois volte a colar o JSON e as vars uma a uma
echo.
pause
