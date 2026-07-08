@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FAZ TUDO 1.0.82 — iOS-only ficha App Store

echo.
echo ============================================================
echo   FAZ TUDO 1.0.82
echo   Commit + push ^| EAS iOS ^| submit iOS automatico
echo   Android: NAO construir nesta release
echo ============================================================
echo.

echo [1/4] Verificacoes...
call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 pause & exit /b 1

echo.
echo [2/4] Commit + push origin main...
git add app\app.config.ts PREPARAR-1.0.82.bat GERAR-IOS-1.0.82.bat AGUARDAR-IOS-E-SUBMETER-1.0.82.bat FAZ-TUDO-1.0.82.bat marketing\NOTAS-1.0.82-APP-STORE.txt
git commit -m "release(1.0.82): iOS-only ficha App Store PAUSA EGO"
if errorlevel 1 (
  echo Sem commit novo ou falhou — a seguir se ja estiver no remoto.
)
git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo [3/4] Enfileirar build EAS (iOS apenas)...
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --ids-file builds-1.0.82.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo [4/4] Aguardar build e submeter iOS...
start "AGUARDAR-IOS-1.0.82" cmd /k "cd /d %~dp0 && call AGUARDAR-IOS-E-SUBMETER-1.0.82.bat"

echo.
echo ============================================================
echo   OK — janela AGUARDAR-IOS-1.0.82 aberta (nao feche).
echo   Connect: versao 1.0.82 + colar marketing\NOTAS-1.0.82-APP-STORE.txt
echo ============================================================
pause
