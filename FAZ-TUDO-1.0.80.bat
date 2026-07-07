@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FAZ TUDO 1.0.80 — API + EAS + teste fechado

echo.
echo ============================================================
echo   FAZ TUDO 1.0.80
echo   API push ^| EAS Android alpha (fechado) ^| iOS TestFlight
echo ============================================================
echo.

echo [1/6] Verificacoes...
call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 pause & exit /b 1

echo.
echo [2/6] Commit + push origin main...
git add app\eas.json app\src\components\PausaEgoScreen.tsx app\src\constants\plans.ts app\src\constants\stripeMonthly.ts ego_api\pausa_exercises.py ego_api\plans.py flask_api.py SYNC-AGENTES-1.0.80.txt SYNC-AGENTES-BOLSO-1.0.80.txt SYNC-AGENTES-API-1.0.80.txt DEPLOY-API-1.0.80.bat RAILWAY-VARS-1.0.80.txt FAZ-TUDO-1.0.80.bat PREPARAR-1.0.80.bat PROMOVER-1.0.80-TESTE-FECHADO.bat
git commit -m "release(1.0.80): PAUSA cartao+CVV, agenda livre, audio 1x, Play alpha"
if errorlevel 1 (
  echo Sem commit novo ou falhou — a seguir se ja estiver no remoto.
)
git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo [3/6] Aguardar Railway ~90s...
timeout /t 90 /nobreak >nul
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 (
  echo AVISO: API ainda a deployar — confira Railway e repita smoke.
)

echo.
echo [4/6] Railway vars — cole RAILWAY-VARS-1.0.80.txt no painel
start "" notepad "%~dp0RAILWAY-VARS-1.0.80.txt"
start "" "https://railway.app"

echo.
echo [5/6] Enfileirar builds EAS (iOS + Android)...
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.80.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo [6/6] Aguardar builds e submeter (Android track=alpha = teste fechado)...
start "AGUARDAR-1.0.80" cmd /k "cd /d %~dp0 && call AGUARDAR-E-SUBMETER-1.0.80.bat"

echo.
echo ============================================================
echo   OK — janela AGUARDAR-1.0.80 aberta (nao feche).
echo   Testadores Android: https://play.google.com/apps/testing/com.egoai.app
echo ============================================================
pause
