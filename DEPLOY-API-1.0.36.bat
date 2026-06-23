@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.36 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.36 — convites + telefone perfil
echo ============================================================
echo.
echo SEM SQL novo. Convites pendentes + PATCH profile phone.
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
echo Ficheiros desta release (1.0.36)...
git add ^
  ego_api/config.py ^
  ego_api/db.py ^
  ego_api/services.py ^
  ego_api/shared_calendars.py ^
  ego_api/streaks.py ^
  ego_api/night_dump.py ^
  flask_api.py ^
  app/app.config.ts ^
  app/app/(main)/_layout.tsx ^
  app/app/(main)/account.tsx ^
  app/app/(main)/agenda.tsx ^
  app/app/(main)/complete-profile.tsx ^
  app/src/api/client.ts ^
  app/src/api/types.ts ^
  app/src/components/PersonaGate.tsx ^
  app/src/components/ProfilePhoneCard.tsx ^
  app/src/components/ProfilePhoneGate.tsx ^
  app/src/components/agenda/AgendaDraftsBanner.tsx ^
  app/src/components/agenda/ClassicSharedAgendaSection.tsx ^
  app/src/components/agenda/EntreNosAgendaSection.tsx ^
  app/src/components/agenda/PendingCalendarInvitesBanner.tsx ^
  app/src/components/agenda/SharedAgendaManual.tsx ^
  app/src/components/agenda/SharedCalendarSocialInvite.tsx ^
  app/src/context/DashboardContext.tsx ^
  app/src/constants/dailyRituals.ts ^
  app/src/hooks/useDailyRitualNotifications.ts ^
  app/src/utils/amanhaRevelado.ts ^
  app/src/utils/dailyCheckInNotification.ts ^
  app/src/utils/phoneBr.ts ^
  app/src/utils/profileComplete.ts ^
  app/src/utils/sharedCalendarLeave.ts ^
  app/src/utils/whatsappShare.ts ^
  ATUALIZAR-1.0.36.bat ^
  GERAR-1.0.36.bat ^
  DEPLOY-API-1.0.36.bat ^
  VALIDAR-1.0.36.bat ^
  SUBMIT-IOS-1.0.36.bat ^
  PUBLICAR-1.0.36-PLAY.bat ^
  VOCE-SO-FAZ-ISTO-1.0.36.txt ^
  marketing/RELEASE-1.0.36.txt ^
  marketing/VALIDAR-1.0.36.txt ^
  marketing/NOTAS-1.0.36-PLAY.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: 1.0.36 convites Entre Nos, telefone obrigatorio e ritual 7h"
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
echo   EGO_LATEST_APP_VERSION=1.0.36
echo   EGO_LATEST_ANDROID_VERSION_CODE=68
pause
