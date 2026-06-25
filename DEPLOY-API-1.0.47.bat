@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API 1.0.47 — convite 20/40/60

echo.
echo ============================================================
echo   DEPLOY API 1.0.47 — EGO de Bolso convite a cada 20 niveis
echo ============================================================
echo.
echo   • Nivel 10 = missao de uso (nao convite)
echo   • Convite obrigatorio: 20, 40, 60...
echo   • Railway redeploy apos git push (~2 min)
echo   • NAO precisa novo build so por isto — mas build 1.0.47 amanha
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

git add ego_api/wellness_journey.py ego_api/config.py flask_api.py marketing/VALIDAR-1.0.47.txt marketing/RELEASE-1.0.47.txt marketing/NOTAS-1.0.47-PLAY.txt AMANHA-1.0.47.bat SUBIR-BUILD-1.0.47.bat VOCE-SO-FAZ-ISTO-1.0.47.txt DEPLOY-API-1.0.47.bat

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo para commitar — deploy ja foi enviado?
  goto :health
)

git commit -m "feat(bolso): convite obrigatorio a cada 20 niveis (1.0.47)"
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
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('API ok=' + $h.ok); Write-Host ('api_build=' + $h.api_build); if ($h.api_build -notmatch 'invite-20') { Write-Host 'AVISO: api_build ainda nao e invite-20 — espere mais 1 min' } } catch { Write-Host 'Ainda a atualizar — tente de novo em 1 min' }"

echo.
echo Depois: SUBIR-BUILD-1.0.47.bat (build amanha)
pause
