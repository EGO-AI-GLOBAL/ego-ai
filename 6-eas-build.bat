@echo off
setlocal
cd /d "%~dp0app"
if errorlevel 1 (
  echo ERRO: nao foi possivel entrar na pasta app.
  pause
  exit /b 1
)
echo.
echo === Build Android production (.aab) v1.0.3 ===
echo Pasta: %CD%
echo.
echo Validando projeto...
call npx expo config --json >nul
if errorlevel 1 (
  echo ERRO: expo config falhou.
  echo Corra: cd app ^&^& npx expo config
  pause
  exit /b 1
)
echo OK.
echo.
echo Se pedir login: eas login
call eas build --platform android --profile production
if errorlevel 1 (
  echo Build falhou.
  pause
  exit /b 1
)
echo Download: https://expo.dev
pause
