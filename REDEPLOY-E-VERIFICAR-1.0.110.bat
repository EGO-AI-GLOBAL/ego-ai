@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Redeploy Railway + verificar API 1.0.110

echo ============================================
echo  PASSO 1 - Vou abrir o Railway no navegador
echo ============================================
echo.
echo  ATENCAO: o botao "Redeploy" repete o MESMO commit antigo.
echo  Para ele ir buscar o codigo novo do GitHub, faz assim:
echo.
echo    1. Projeto EGO-AI
echo    2. Servico: ego-ai-production
echo    3. Separador "Variables"
echo    4. Muda o valor de EGO_DEPLOY_TAG para: nome-pet-1-0-110
echo       (se nao existir, cria a variavel com esse nome e valor)
echo    5. Confirma - o Railway arranca um deploy novo sozinho
echo    6. Espera ficar "Success" / "Active"
echo.
pause
start "" "https://railway.app"

echo.
echo ============================================
echo  PASSO 2 - Agora eu verifico sozinho
echo ============================================
echo  Espero ate a API nova responder (ate 10 min).
echo  Podes deixar esta janela aberta.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$alvo='2026-08-08-monstrinhos-finch-v3-nome-pet-level-up';" ^
  "$url='https://ego-ai-production-a2c2.up.railway.app/api/v1/health';" ^
  "for ($i=1; $i -le 40; $i++) {" ^
  "  try { $r = Invoke-RestMethod -Uri $url -TimeoutSec 20 } catch { $r = $null };" ^
  "  if ($r -and $r.api_build -eq $alvo) {" ^
  "    Write-Host '';" ^
  "    Write-Host '==============================================' -ForegroundColor Green;" ^
  "    Write-Host ' API NOVA NO AR! api_build=' $r.api_build -ForegroundColor Green;" ^
  "    Write-Host ' Dar nome ao monstrinho ja funciona.' -ForegroundColor Green;" ^
  "    Write-Host '==============================================' -ForegroundColor Green;" ^
  "    exit 0" ^
  "  };" ^
  "  $atual = if ($r) { $r.api_build } else { 'sem resposta' };" ^
  "  Write-Host ('[' + $i + '/40] ainda a antiga: ' + $atual);" ^
  "  Start-Sleep -Seconds 15" ^
  "};" ^
  "Write-Host '';" ^
  "Write-Host 'AINDA NAO SUBIU depois de 10 min.' -ForegroundColor Yellow;" ^
  "Write-Host 'Confirma no Railway se o deploy ficou Success (nao Failed).' -ForegroundColor Yellow;" ^
  "exit 1"

echo.
pause
