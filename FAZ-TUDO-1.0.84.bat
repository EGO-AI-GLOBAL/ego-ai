@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FAZ TUDO 1.0.84 — Tríade Silenciosa

echo.
echo ============================================================
echo   FAZ TUDO 1.0.84
echo   Commit + push ^| EAS iOS+Android ^| submit iOS auto
echo   Android: upload manual (SUBIR-ANDROID-FECHADO-MANUAL.bat)
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
git add app\app.config.ts PREPARAR-1.0.84.bat GERAR-1.0.84.bat AGUARDAR-E-SUBMETER-1.0.84.bat FAZ-TUDO-1.0.84.bat marketing\NOTAS-1.0.84-APP-STORE.txt marketing\NOTAS-1.0.84-PLAY.txt SYNC-AGENTES-1.0.84.txt
git commit -m "release(1.0.84): triade silenciosa PAUSA iOS auto Android manual"
if errorlevel 1 (
  echo Sem commit novo ou falhou — a seguir se ja estiver no remoto.
)
git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo [3/4] Enfileirar builds EAS (iOS + Android)...
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 (
  echo AVISO sync-check falhou — a seguir com --skip-sync
  call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --skip-sync --ids-file builds-1.0.84.ids.json
) else (
  call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.84.ids.json
)
if errorlevel 1 pause & exit /b 1

echo.
echo [4/4] Aguardar e submeter iOS (janela separada)...
start "AGUARDAR-1.0.84" cmd /k "cd /d %~dp0 && call AGUARDAR-E-SUBMETER-1.0.84.bat"

echo.
echo ============================================================
echo   OK — nao feche AGUARDAR-1.0.84
echo   iOS: Connect 1.0.84 build 86
echo   Android: SUBIR-ANDROID-FECHADO-MANUAL.bat quando pronto
echo ============================================================
pause
