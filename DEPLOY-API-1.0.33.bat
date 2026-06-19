@echo off
chcp 65001 >nul
cd /d "%~dp0"
title EGO-AI — deploy API 1.0.33 (Railway)

echo.
echo ============================================================
echo   Deploy API 1.0.33 no Railway (via git push)
echo ============================================================
echo.
echo Inclui: Entre Nos, Desabafo, confirmar/recusar convites
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
echo Ficheiros desta release (API + app 1.0.33)...
git add ^
  ego_api/shared_calendars.py ^
  ego_api/shared_calendar_notify.py ^
  ego_api/family_pilot.py ^
  ego_api/night_dump.py ^
  ego_api/delegation_db.py ^
  ego_api/streaks.py ^
  ego_api/config.py ^
  ego_api/services.py ^
  ego_api/habits_db.py ^
  ego_api/chat_schedule.py ^
  flask_api.py ^
  scripts/regression_guard.py ^
  supabase/COLE-1.0.33-ENTRE-NOS.sql ^
  supabase/COLE-ENTRE-NOS-INVITE.sql ^
  supabase/migrations/20260617200000_delegation_requests.sql ^
  supabase/migrations/20260617300000_entre_nos_invite_status.sql ^
  app/app.config.ts ^
  app/src/api/client.ts ^
  app/src/api/types.ts ^
  app/src/utils/entreNos.ts ^
  app/src/hooks/useDailyRitualNotifications.ts ^
  app/src/components/agenda/SharedAgendaManual.tsx ^
  app/src/components/agenda/SharedEventRow.tsx ^
  app/src/components/agenda/AgendaTabBar.tsx ^
  app/src/components/agenda/AgendaDraftsBanner.tsx ^
  app/src/components/agenda/DelegationRequestsBanner.tsx ^
  app/src/components/StreakBadge.tsx ^
  app/src/storage/streakCache.ts ^
  "app/app/(main)/agenda.tsx" ^
  "app/app/(main)/chat.tsx" ^
  "app/app/(main)/shared-calendar/[id].tsx" ^
  DEPLOY-API-1.0.33.bat ^
  DEPLOY-1.0.33-RAILWAY.bat ^
  ABRIR-SQL-1.0.33.bat ^
  GERAR-1.0.33.bat ^
  VALIDAR-1.0.33.bat ^
  SUBMIT-IOS-1.0.33.bat ^
  PUBLICAR-1.0.33-PLAY.bat

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged. Se ja fez push, aguarde redeploy Railway ~2 min.
  goto :health
)

git commit -m "feat: 1.0.33 Entre Nos convites, Desabafo agenda compartilhada, streaks"
if errorlevel 1 (
  echo Commit falhou.
  pause
  exit /b 1
)

echo.
echo Push para GitHub (Railway redeploy automatico)...
git push origin main
if errorlevel 1 (
  echo.
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
echo Proximo passo (depois de OK): variaveis Railway 1.0.33 / code 65
pause
