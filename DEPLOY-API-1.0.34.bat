@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.34 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.34 — hotfix agenda compartilhada + Entre Nos
echo ============================================================
echo.
echo SEM SQL novo — Supabase 1.0.33 ja aplicado.
echo.

python scripts\regression_guard.py
if errorlevel 1 (
  echo regression_guard FALHOU — corrija antes do push.
  pause
  exit /b 1
)

python scripts\smoke_test_api.py
if errorlevel 1 (
  echo smoke_test FALHOU — corrija antes do push.
  pause
  exit /b 1
)

echo.
echo Ficheiros desta release (hotfix 1.0.34)...
git add ^
  ego_api/shared_calendars.py ^
  ego_api/config.py ^
  flask_api.py ^
  scripts/regression_guard.py ^
  app/app.config.ts ^
  app/src/utils/entreNos.ts ^
  app/src/components/agenda/AgendaTabBar.tsx ^
  app/src/components/agenda/SharedAgendaManual.tsx ^
  app/src/components/agenda/ClassicSharedAgendaSection.tsx ^
  app/src/components/agenda/EntreNosAgendaSection.tsx ^
  "app/app/(main)/agenda.tsx" ^
  DEPLOY-API-1.0.34.bat ^
  GERAR-1.0.34.bat ^
  VALIDAR-1.0.34.bat ^
  SUBMIT-IOS-1.0.34.bat ^
  PUBLICAR-1.0.34-PLAY.bat ^
  marketing/RELEASE-1.0.34.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "fix: 1.0.34 agenda compartilhada restaurada + Entre Nos 2 pessoas"
if errorlevel 1 (
  echo Commit falhou.
  pause
  exit /b 1
)

echo.
echo Push para GitHub (Railway redeploy automatico)...
git push origin main
if errorlevel 1 (
  echo Push falhou — faca login Git e: git push origin main
  pause
  exit /b 1
)

:health
echo.
echo Aguardando redeploy (~90s)...
timeout /t 90 /nobreak >nul
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('API ok=' + $h.ok + ' api_build=' + $h.api_build + ' latest=' + $h.app_update.latest_version) } catch { Write-Host 'Health ainda a atualizar — tente de novo em 1 min' }"

echo.
echo Proximo: Railway EGO_LATEST_APP_VERSION=1.0.34 code 66
pause
