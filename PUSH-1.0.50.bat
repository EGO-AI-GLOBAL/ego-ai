@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Push 1.0.50 — Railway redeploy API

echo.
echo Enviando 2 commits 1.0.50 para origin/main...
echo   • 82efa8c release(1.0.50)
echo   • 09ba80d chore build automatico
echo.

git push origin main

if errorlevel 1 (
  echo.
  echo FALHOU — correr manualmente: git push origin main
  pause
  exit /b 1
)

echo.
echo OK — Railway vai redeployar a API automaticamente.
echo Depois: ABRIR-SUPABASE-RESET-SENHA.bat (5 min, uma vez)
pause
