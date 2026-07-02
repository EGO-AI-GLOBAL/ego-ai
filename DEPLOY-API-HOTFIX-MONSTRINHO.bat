@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Hotfix API — label Sol em vez de Bem

echo.
echo ============================================================
echo   HOTFIX — Monstrinhos: mostra Sol/Brisa (nao Bem/Peso)
echo ============================================================
echo.
echo Corrige ego_api/daily_care.py + app DailyCareChallenge.tsx
echo Railway redeploy automatico apos git push (~2 min)
echo.
echo NAO precisa novo build iOS/Android para este fix.
echo No app: Monstrinhos ^> puxar para baixo ^> atualizar
echo.

call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 (
  echo regression_guard FALHOU.
  pause
  exit /b 1
)

call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 (
  echo smoke_test FALHOU.
  pause
  exit /b 1
)

git add ego_api/daily_care.py app/src/components/DailyCareChallenge.tsx app/src/constants/moodMonsters.ts app/src/components/moodMonsters/MoodMonsterScene.tsx app/src/components/moodMonsters/MoodJournalWeek.tsx app/src/utils/moodJournalInsights.ts flask_api.py

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo para commitar — hotfix ja foi enviado?
  goto :health
)

git commit -m "fix(monstrinhos): labels Sol/Brisa no diario e UI (nao Bem/Peso)"
if errorlevel 1 (
  echo Commit falhou.
  pause
  exit /b 1
)

echo.
echo Push para GitHub...
git push origin main
if errorlevel 1 (
  echo Push falhou — faca login e: git push origin main
  pause
  exit /b 1
)

:health
echo.
echo Aguardando Railway (~90s)...
timeout /t 90 /nobreak >nul
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('API ok=' + $h.ok); Write-Host ('api_build=' + $h.api_build) } catch { Write-Host 'Ainda a atualizar — tente de novo em 1 min' }"

echo.
echo Confirmar api_build: 2026-07-01-hotfix-monstrinho-sol-brisa
echo No telemovel: Monstrinhos ^> puxar ecrã para baixo ^> deve dizer Sol
pause
