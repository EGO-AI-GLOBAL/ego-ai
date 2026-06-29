@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API — chat hotfix 1.0.57

echo.
echo ============================================================
echo   API Railway — chat nao rebenta ao enviar mensagem
echo ============================================================
echo.
echo Corrige: bolso/jornada com dados invalidos + erros Gemini visiveis
echo NAO precisa novo build iOS/Android — so Redeploy Railway (~2 min)
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

git add ego_api/avatar_memory.py flask_api.py DEPLOY-API-CHAT-1.0.57.bat

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo para commitar.
  goto :health
)

git commit -m "fix(api): avatar_memory usa ego_supabase no Railway (sem pacote supabase)"
git push origin main

:health
echo.
echo Aguardando Railway (~90s)...
timeout /t 90 /nobreak >nul
powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 30; Write-Host ('ok=' + $h.ok); Write-Host ('api_build=' + $h.api_build); if ($h.api_build -notmatch '1.0.57-chat-hotfix3') { Write-Host 'AVISO: ainda nao atualizou — espere 1 min e teste de novo' } } catch { Write-Host 'Health ainda a atualizar' }"
echo.
echo Teste no iPhone: enviar «oi» ou «boa noite» no chat.
pause
