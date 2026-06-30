@echo off
chcp 65001 >nul
cd /d "%~dp0app"
title Submit Android 1.0.67 — Play

if not exist "play-store-service-account.json" (
  echo.
  echo FALTA o ficheiro JSON no PC — nao basta estar na Google Cloud.
  echo.
  echo 1. Google Cloud ^> ego-play-integrity ^> Chaves ^> Adicionar chave ^> JSON
  echo 2. Copie o ficheiro descarregado para:
  echo    %~dp0app\play-store-service-account.json
  echo 3. Rode este .bat outra vez
  echo.
  pause
  exit /b 1
)

set NODE_TLS_REJECT_UNAUTHORIZED=0
call npx eas submit --platform android --id 889240f5-c461-406d-9ba6-5ab03786116a --non-interactive
if errorlevel 1 pause & exit /b 1
echo OK — Play Console ^> teste interno ^> 1.0.67
pause
