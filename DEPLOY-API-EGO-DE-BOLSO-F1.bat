@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API EGO de Bolso Fase 1

echo.
echo ============================================================
echo   Deploy API — EGO de Bolso Fase 1 (rename + share copy)
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

git add ^
  ego_api/services.py ^
  ego_api/wellness_journey.py ^
  flask_api.py ^
  scripts/regression_guard.py ^
  app/src/components/EgoDeBolsoChatCard.tsx ^
  app/src/components/PocketCompanionShareModal.tsx ^
  app/src/components/SocialShareModal.tsx ^
  app/src/components/WellnessJourneyCard.tsx ^
  app/src/constants/socialProfiles.ts ^
  app/src/utils/whatsappShare.ts ^
  app/src/utils/trialAccess.ts ^
  app/src/components/TrialBanner.tsx ^
  app/src/components/AppDrawer.tsx ^
  app/src/components/agenda/PersonalAgendaManual.tsx ^
  app/app/(main)/chat.tsx ^
  app/app/(main)/wellness-journey.tsx ^
  DEPLOY-API-EGO-DE-BOLSO-F1.bat

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: EGO de Bolso Fase 1 — rename, share viral e mini-card no chat"
if errorlevel 1 ( pause & exit /b 1 )

git push origin main
if errorlevel 1 ( pause & exit /b 1 )

:health
echo.
echo Aguardando redeploy (~90s)...
timeout /t 90 /nobreak >nul
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('API ok=' + $h.ok + ' api_build=' + $h.api_build) } catch { Write-Host 'Health ainda a atualizar — tente de novo em 1 min' }"
pause
