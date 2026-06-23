@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.40 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.40 — Monstrinhos + Companheiro
echo ============================================================
echo.
echo SEM SQL novo. Copy API + defaults de versao.
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
echo Ficheiros desta release (1.0.40)...
git add ^
  ego_api/config.py ^
  ego_api/daily_care.py ^
  ego_api/services.py ^
  ego_api/wellness_journey.py ^
  flask_api.py ^
  scripts/regression_guard.py ^
  app/app.config.ts ^
  app/app/(main)/chat.tsx ^
  app/app/(main)/daily-care.tsx ^
  app/app/(main)/wellness-journey.tsx ^
  app/src/components/AppDrawer.tsx ^
  app/src/components/DailyCareChallenge.tsx ^
  app/src/components/DailyCareShareModal.tsx ^
  app/src/components/MoodMonstersShareModal.tsx ^
  app/src/components/PocketCompanionShareModal.tsx ^
  app/src/components/SocialShareModal.tsx ^
  app/src/components/TrialBanner.tsx ^
  app/src/components/WellnessJourneyCard.tsx ^
  app/src/components/agenda/PersonalAgendaManual.tsx ^
  app/src/utils/streakReactions.ts ^
  app/src/utils/trialAccess.ts ^
  app/src/utils/whatsappShare.ts ^
  GERAR-1.0.40.bat ^
  SUBMIT-IOS-1.0.40.bat ^
  PUBLICAR-1.0.40-PLAY.bat ^
  VALIDAR-1.0.40.bat ^
  DEPLOY-API-1.0.40.bat ^
  VOCE-SO-FAZ-ISTO-1.0.40.txt ^
  marketing/RELEASE-1.0.40.txt ^
  marketing/NOTAS-1.0.40-PLAY.txt ^
  marketing/VALIDAR-1.0.40.txt ^
  marketing/POST-VIDEO-1.0.40.txt ^
  marketing/CAPCUT-FOTOS-1.0.40/LEIA-ME.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: 1.0.40 Monstrinhos do Humor, Companheiro de Bolso e chat sem Ofensiva"
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
echo Railway (banner de atualizacao):
echo   EGO_LATEST_APP_VERSION=1.0.40
echo   EGO_LATEST_ANDROID_VERSION_CODE=75
echo   EGO_APP_UPDATE_MESSAGE=1.0.40: Monstrinhos do Humor + Companheiro de Bolso...
pause
