@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.42 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.42 — Monstrinhos Finch (missões + sementes)
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

git add ^
  ego_api/config.py ^
  ego_api/daily_care.py ^
  flask_api.py ^
  scripts/regression_guard.py ^
  app/app.config.ts ^
  app/src/api/client.ts ^
  app/src/api/types.ts ^
  app/src/components/DailyCareChallenge.tsx ^
  app/src/components/moodMonsters/ ^
  app/src/constants/moodMonsters.ts ^
  DEPLOY-API-1.0.42.bat ^
  GERAR-1.0.42.bat ^
  SUBMIT-IOS-1.0.42.bat ^
  PUBLICAR-1.0.42-PLAY.bat ^
  VALIDAR-1.0.42.bat ^
  VOCE-SO-FAZ-ISTO-1.0.42.txt ^
  marketing/RELEASE-1.0.42.txt ^
  marketing/NOTAS-1.0.42-PLAY.txt ^
  marketing/VALIDAR-1.0.42.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: 1.0.42 Monstrinhos Finch — missões diárias, sementes e aventura"
if errorlevel 1 ( pause & exit /b 1 )

git push origin main
if errorlevel 1 ( pause & exit /b 1 )

:health
echo.
echo Aguardando redeploy (~90s)...
timeout /t 90 /nobreak >nul
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('API ok=' + $h.ok + ' api_build=' + $h.api_build + ' latest=' + $h.app_update.latest_version) } catch { Write-Host 'Health ainda a atualizar — tente de novo em 1 min' }"

echo.
echo Railway (opcional, defaults no codigo ja sao 1.0.42 / 77):
echo   EGO_LATEST_APP_VERSION=1.0.42
echo   EGO_LATEST_ANDROID_VERSION_CODE=77
pause
