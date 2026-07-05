@echo off
chcp 65001 >nul
title EGO-AI — Hotfix chat Android (testadores)
echo.
echo ============================================================
echo  URGENTE — Testadores Android nao conseguem mandar mensagem
echo ============================================================
echo.
echo CAUSA PROVAVEL:
echo   Railway com EGO_PLAY_INTEGRITY_MODE=enforce
echo   + app cortava token Play Integrity aos 800 ms (build 1.0.76/77)
echo.
echo CORRECAO IMEDIATA (sem nova build — so Railway):
echo   1. Abra railway.app - servico ego-ai-api - Variables
echo   2. Mude:  EGO_PLAY_INTEGRITY_MODE=monitor
echo      (mantenha EGO_PLAY_INTEGRITY=1)
echo   3. Redeploy / Deploy
echo   4. Teste no celular: texto «Oi» no chat
echo.
echo Link teste interno Play (testadores devem instalar daqui):
echo   https://play.google.com/apps/testing/com.egoai.app
echo.
echo === Estado actual da API ===
powershell -NoProfile -Command ^
  "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 25; Write-Host ('ok: ' + $h.ok); Write-Host ('api_build: ' + $h.api_build); if ($h.play_integrity) { Write-Host ('play_integrity.mode: ' + $h.play_integrity.mode); if ($h.play_integrity.mode -eq 'enforce') { Write-Host ''; Write-Host '>>> MUDE PARA monitor NO RAILWAY AGORA <<<' -ForegroundColor Red } else { Write-Host 'modo OK para testadores (monitor)' -ForegroundColor Green } } } catch { Write-Host 'Nao consegui ler /health — verifique internet' -ForegroundColor Yellow }"
echo.
echo Build 1.0.78 (amanha): corrige timeout integrity no app (sem corte 800 ms).
echo.
pause
