@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API 1.0.41

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

git add ego_api/daily_care.py ego_api/wellness_journey.py ego_api/services.py ego_api/config.py flask_api.py scripts/regression_guard.py app/app.config.ts app/src/api/types.ts app/src/constants/moodMonsters.ts app/src/components/moodMonsters/ app/src/components/companion/ app/src/components/DailyCareChallenge.tsx app/src/components/WellnessJourneyCard.tsx app/src/components/PocketCompanionShareModal.tsx app/app/(main)/daily-care.tsx app/app/(main)/wellness-journey.tsx GERAR-1.0.41.bat SUBMIT-IOS-1.0.41.bat PUBLICAR-1.0.41-PLAY.bat VALIDAR-1.0.41.bat DEPLOY-API-1.0.41.bat marketing/RELEASE-1.0.41.txt marketing/NOTAS-1.0.41-PLAY.txt marketing/VALIDAR-1.0.41.txt VOCE-SO-FAZ-ISTO-1.0.41.txt

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo staged.
  goto :done
)

git commit -m "feat: 1.0.41 jardim Finch monstrinhos + companheiro visual tamagotchi"
if errorlevel 1 ( pause & exit /b 1 )

git push origin main
if errorlevel 1 ( pause & exit /b 1 )

:done
echo Railway vars: EGO_LATEST_APP_VERSION=1.0.41  EGO_LATEST_ANDROID_VERSION_CODE=76
pause
