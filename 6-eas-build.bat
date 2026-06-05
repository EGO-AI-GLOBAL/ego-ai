@echo off
cd /d "%~dp0"
echo.
echo === EGO-AI 1.0.10 - build Android .aab ===
echo.
echo Verificacao automatica antes do upload...
set NODE_TLS_REJECT_UNAUTHORIZED=0
python scripts\checklist_launch.py --repair
if errorlevel 1 (
  echo.
  echo Build cancelado - corrija os erros acima.
  pause
  exit /b 1
)

cd /d "%~dp0app"
set NODE_TLS_REJECT_UNAUTHORIZED=0
set EAS_BUILD_NO_EXPO_GO_WARNING=true
echo.
echo A enviar build para a nuvem Expo - 15 a 30 min...
echo Nao feche esta janela.
echo.
call npx eas-cli env:create --name EXPO_PUBLIC_API_URL --value https://ego-ai-production-a2c2.up.railway.app --environment production --scope project --visibility plaintext --force --non-interactive 2>nul
call npx eas-cli build --platform android --profile production
echo.
echo Fim. Baixe o .aab em https://expo.dev - Builds
pause
