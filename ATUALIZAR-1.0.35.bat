@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — preparar atualização 1.0.35

echo.
echo ============================================================
echo   EGO-AI 1.0.35 — Fase 1 (Ofensiva + WhatsApp + Amanhã)
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 (
  echo REGRESSION GUARD falhou.
  pause
  exit /b 1
)

python scripts\smoke_test_api.py
if errorlevel 1 (
  echo SMOKE TEST falhou.
  pause
  exit /b 1
)

echo.
echo Instalando dependencias do app (react-native-view-shot)...
cd app
set NODE_TLS_REJECT_UNAUTHORIZED=0
call npm install
if errorlevel 1 (
  echo npm install falhou — tente manualmente: cd app ^&^& npm install
  cd ..
  pause
  exit /b 1
)
cd ..

call VERIFICAR-ANTES-DO-BUILD.bat
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Pronto para build. Proximos passos:
echo ============================================================
echo   1. DEPLOY-API-1.0.35.bat  (push API + Railway vars)
echo   2. GERAR-1.0.35.bat       (EAS iOS 18 + Android 67)
echo   3. SUBMIT-IOS-1.0.35.bat + PUBLICAR-1.0.35-PLAY.bat
echo   4. VALIDAR-1.0.35.bat
echo.
start "" notepad "%CD%\marketing\RELEASE-1.0.35.txt"
pause
