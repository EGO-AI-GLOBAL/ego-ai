@echo off
chcp 65001 >nul
cd /d "%~dp0"
title FAZ TUDO 1.0.81 — hotfix sessão + EAS

echo.
echo ============================================================
echo   FAZ TUDO 1.0.81
echo   Commit + push ^| EAS iOS+Android ^| iOS submit auto
echo   Android: upload manual no teste fechado
echo ============================================================
echo.

echo [1/5] Verificacoes...
call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 pause & exit /b 1

echo.
echo [2/5] Commit + push origin main...
git add app\app.config.ts app\src\context\AuthContext.tsx app\src\storage\authAppVersion.ts app\src\storage\freshInstallGuard.ts app\src\storage\sessionStorage.ts scripts\onboarding_guard.py PREPARAR-1.0.81.bat GERAR-1.0.81.bat AGUARDAR-E-SUBMETER-1.0.81.bat FAZ-TUDO-1.0.81.bat RAILWAY-VARS-1.0.81.txt SYNC-AGENTES-1.0.81.txt SYNC-AGENTES-MONSTRINHOS-1.0.81.txt SYNC-AGENTES-BOLSO-1.0.81.txt SYNC-AGENTES-API-1.0.81.txt marketing\NOTAS-1.0.81-APP-STORE.txt marketing\NOTAS-1.0.81-PLAY.txt
git commit -m "$(cat <<'EOF'
release(1.0.81): hotfix sessão persistente ao reabrir o app

Marcador duplo install + espelho AsyncStorage evita logout falso a cada abertura.
EOF
)"
if errorlevel 1 (
  echo Sem commit novo ou falhou — a seguir se ja estiver no remoto.
)
git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo [3/5] Railway vars — cole RAILWAY-VARS-1.0.81.txt apos builds prontas
start "" notepad "%~dp0RAILWAY-VARS-1.0.81.txt"

echo.
echo [4/5] Enfileirar builds EAS (iOS + Android)...
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 pause & exit /b 1
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.81.ids.json
if errorlevel 1 pause & exit /b 1

echo.
echo [5/5] Aguardar builds e submeter iOS...
start "AGUARDAR-1.0.81" cmd /k "cd /d %~dp0 && call AGUARDAR-E-SUBMETER-1.0.81.bat"

echo.
echo ============================================================
echo   OK — janela AGUARDAR-1.0.81 aberta (nao feche).
echo   Android manual: SUBIR-ANDROID-FECHADO-MANUAL.bat
echo   App Store Connect: versao 1.0.81 + enviar revisao
echo ============================================================
pause
