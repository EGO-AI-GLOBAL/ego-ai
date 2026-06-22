@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.35 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.35 — defaults banner atualizacao
echo ============================================================
echo.
echo SEM SQL novo. App-only: Ofensiva + WhatsApp + Amanha revelado.
echo.

python scripts\regression_guard.py
if errorlevel 1 (
  echo regression_guard FALHOU.
  pause
  exit /b 1
)

python scripts\smoke_test_api.py
if errorlevel 1 (
  echo smoke_test FALHOU.
  pause
  exit /b 1
)

echo.
echo Ficheiros desta release (1.0.35)...
git add ^
  ego_api/config.py ^
  flask_api.py ^
  app/app.config.ts ^
  app/package.json ^
  app/src/utils/streakReactions.ts ^
  app/src/utils/amanhaRevelado.ts ^
  app/src/utils/whatsappShare.ts ^
  app/src/components/StreakBadge.tsx ^
  app/src/components/StreakShareModal.tsx ^
  app/src/components/agenda/AgendaDraftsBanner.tsx ^
  app/src/components/agenda/EntreNosAgendaSection.tsx ^
  app/src/components/agenda/SharedEventRow.tsx ^
  "app/app/(main)/chat.tsx" ^
  ATUALIZAR-1.0.35.bat ^
  GERAR-1.0.35.bat ^
  DEPLOY-API-1.0.35.bat ^
  VALIDAR-1.0.35.bat ^
  SUBMIT-IOS-1.0.35.bat ^
  PUBLICAR-1.0.35-PLAY.bat ^
  marketing/RELEASE-1.0.35.txt ^
  marketing/VALIDAR-1.0.35.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: 1.0.35 card ofensiva, WhatsApp Entre Nos e amanha revelado"
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
echo Railway (obrigatorio para banner de atualizacao):
echo   EGO_LATEST_APP_VERSION=1.0.35
echo   EGO_LATEST_ANDROID_VERSION_CODE=67
pause
