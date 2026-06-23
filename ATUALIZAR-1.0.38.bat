@echo off

chcp 65001 >nul

cd /d "%~dp0"

title EGO-AI — preparar atualização 1.0.38



echo.

echo ============================================================

echo   EGO-AI 1.0.38 — Desafio Diário + Jornada + trial banner

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



cd app

set NODE_TLS_REJECT_UNAUTHORIZED=0

call npm install

if errorlevel 1 (

  echo npm install falhou.

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

echo   Pronto para build. MANUAL: ver PASO-A-PASSO-MANUAL-1.0.38.md

echo ============================================================

echo   1. git push main

echo   2. Railway redeploy + variaveis (ver doc)

echo   3. GERAR-1.0.38.bat

echo   4. SUBMIT-IOS-1.0.38.bat + PUBLICAR-1.0.38-PLAY.bat

echo   5. VALIDAR-1.0.38.bat

echo.

start "" notepad "%CD%\PASO-A-PASSO-MANUAL-1.0.38.md"

start "" notepad "%CD%\marketing\RELEASE-1.0.38.txt"

pause
