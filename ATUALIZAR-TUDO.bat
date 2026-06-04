@echo off
setlocal
cd /d "%~dp0"
title EGO-AI — Atualizar tudo

echo.
echo ============================================================
echo   EGO-AI — atualizacao completa (API + app + build)
echo ============================================================
echo.

REM --- 1) API Railway ---
echo [1/5] Verificando API Railway...
powershell -NoProfile -Command ^
  "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 20; if ($h.ok) { Write-Host '      API: ONLINE' -ForegroundColor Green } else { Write-Host '      API: resposta inesperada' -ForegroundColor Yellow } } catch { Write-Host '      API: OFFLINE' -ForegroundColor Red }"
powershell -NoProfile -Command ^
  "try { $p = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/plans' -TimeoutSec 20; if ($p.launch_offer) { Write-Host '      Plano R$ 9,90: ATIVO na API' -ForegroundColor Green } else { Write-Host '      Plano R$ 9,90: FALTA variavel no Railway' -ForegroundColor Yellow; Write-Host '      Railway -^> Variables -^> STRIPE_CHECKOUT_LAUNCH_URL' -ForegroundColor Yellow; Write-Host '      Valor: https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K' -ForegroundColor Gray } } catch { }"

echo.
echo [2/5] Sincronizando app -^> app_local_backup...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-app-to-backup.ps1"
if errorlevel 1 goto :erro

echo.
echo [3/5] Git: commit e push (API redeploy no Railway)...
git add app/app/login.tsx app/app/signup.tsx app/src/components/PasswordField.tsx app/app.config.ts scripts/sync-app-to-backup.ps1 ATUALIZAR-TUDO.bat 0-iniciar-tudo.bat 1-iniciar-expo.bat 2>nul
git diff --cached --quiet
if %errorlevel%==0 (
  echo      Nada novo para commitar no app.
) else (
  git commit -m "feat(app): ver senha no login/cadastro e versao 1.0.4"
  if errorlevel 1 goto :erro
  git push origin main
  if errorlevel 1 (
    echo      Push falhou — faca login no Git e: git push origin main
  ) else (
    echo      Push OK — Railway deve redeployar em ~2 min.
  )
)

echo.
echo [4/5] Expo (teste local) — nova janela...
if not exist "app_local_backup\.env" (
  echo EXPO_PUBLIC_API_URL=https://ego-ai-production-a2c2.up.railway.app> "app_local_backup\.env"
  echo EXPO_PUBLIC_FLASK_PROXY=https://ego-ai-production-a2c2.up.railway.app>> "app_local_backup\.env"
)
start "EGO-AI Expo" cmd /k "cd /d "%~dp0app_local_backup" && npm run start:lan"

echo.
echo [5/5] Build Play Store (EAS) — pode demorar 15-30 min...
echo      Precisa: eas login (use 5-eas-login.bat se necessario)
set NODE_TLS_REJECT_UNAUTHORIZED=0
set EAS_BUILD_NO_EXPO_GO_WARNING=true
cd /d "%~dp0app_local_backup"
call npx eas-cli build --platform android --profile production --non-interactive
if errorlevel 1 (
  echo.
  echo Build EAS falhou ou precisa login. Corra depois: 4-build-playstore.bat
) else (
  echo.
  echo Build OK — baixe o .aab em https://expo.dev e envie ao teste interno Play.
)

echo.
echo ============================================================
echo   Checklist manual no Railway (se plano 9,90 nao aparecer):
echo   STRIPE_CHECKOUT_LAUNCH_URL=https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K
echo   Depois: Redeploy no painel Railway
echo ============================================================
pause
goto :eof

:erro
echo.
echo Erro num passo. Veja mensagens acima.
pause
exit /b 1
