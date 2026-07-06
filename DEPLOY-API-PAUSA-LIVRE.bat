@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API — PAUSA livre para todos

echo.
echo ============================================================
echo   PAUSA EGO — 20 tecnicas para qualquer plano
echo ============================================================
echo.
echo Railway redeploy apos git push (~2 min)
echo No app: PAUSA EGO ^> puxar para baixo
echo.
echo NOTA: rotacao diaria no app precisa build 1.0.79 (parseDashboard + IAP fix)
echo.

call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 pause & exit /b 1

call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 pause & exit /b 1

git add ego_api\pausa_exercises.py ego_api\pausa_ego.py flask_api.py scripts\regression_guard.py app\src\components\PausaEgoScreen.tsx
git commit -m "feat(api): PAUSA livre — 20 tecnicas para todos os planos"
if errorlevel 1 (
  echo Nada para commitar ou commit falhou.
  pause
  exit /b 1
)

git push origin main
if errorlevel 1 pause & exit /b 1

echo.
echo OK — aguarde ~2 min Railway. Depois puxe para baixo em PAUSA EGO.
pause
