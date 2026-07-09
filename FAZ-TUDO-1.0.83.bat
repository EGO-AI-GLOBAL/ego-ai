@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FAZ TUDO 1.0.83 — iOS subtítulo + idioma PT-BR

echo.
echo ============================================================
echo   FAZ TUDO 1.0.83
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
git add app\app.config.ts PREPARAR-1.0.83.bat GERAR-IOS-1.0.83.bat AGUARDAR-IOS-E-SUBMETER-1.0.83.bat FAZ-TUDO-1.0.83.bat marketing\NOTAS-1.0.83-APP-STORE.txt
git commit -m "release(1.0.83): iOS-only subtitulo ASO e idioma pt-BR"
if errorlevel 1 (
  echo Sem commit novo ou falhou — a seguir se ja estiver no remoto.
)
git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo [3/4] Enfileirar build EAS (iOS apenas)...
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue-ios --ids-file builds-1.0.83.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo [4/4] Aguardar build e submeter iOS...
start "AGUARDAR-IOS-1.0.83" cmd /k "cd /d %~dp0 && call AGUARDAR-IOS-E-SUBMETER-1.0.83.bat"

echo.
echo ============================================================
echo   OK — janela AGUARDAR-IOS-1.0.83 aberta (nao feche).
echo   Connect: versao 1.0.83 + build 84 + NOTAS-1.0.83-APP-STORE.txt
echo ============================================================
pause
