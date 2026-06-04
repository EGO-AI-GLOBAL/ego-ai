@echo off
cd /d "%~dp0"
echo.
echo === EGO-AI: colocar no ar ===
echo API Railway: https://ego-ai-production-a2c2.up.railway.app
echo.

powershell -NoProfile -Command "try { $h = Invoke-RestMethod -Uri 'https://ego-ai-production-a2c2.up.railway.app/api/v1/health' -TimeoutSec 15; if ($h.ok) { Write-Host 'API: ONLINE' -ForegroundColor Green } else { Write-Host 'API: resposta estranha' -ForegroundColor Yellow } } catch { Write-Host 'API: OFFLINE ou sem internet' -ForegroundColor Red; Write-Host $_.Exception.Message }"

if not exist "app\.env" (
  echo Criando app\.env com URL da Railway...
  (
    echo EXPO_PUBLIC_API_URL=https://ego-ai-production-a2c2.up.railway.app
    echo EXPO_PUBLIC_FLASK_PROXY=https://ego-ai-production-a2c2.up.railway.app
  ) > "app\.env"
)

echo.
echo A iniciar Expo (deixe esta janela ABERTA)...
echo PC browser: http://localhost:8082
echo Telefone: escaneie o QR no Expo Go (mesma Wi-Fi)
echo.
cd /d "%~dp0app_local_backup"
call npm run start:lan
pause
