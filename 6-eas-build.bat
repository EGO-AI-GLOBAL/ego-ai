@echo off
setlocal
cd /d "%~dp0app"
if errorlevel 1 (
  echo ERRO: nao foi possivel entrar na pasta app.
  pause
  exit /b 1
)
if not exist package.json (
  echo ERRO: falta app\package.json nesta pasta.
  echo Pasta atual: %CD%
  pause
  exit /b 1
)
if not exist eas.json (
  echo ERRO: falta app\eas.json nesta pasta.
  echo Pasta atual: %CD%
  pause
  exit /b 1
)
echo.
echo === Build Android production (.aab) v1.0.3 ===
echo Pasta: %CD%
echo.
echo A URL da API ja esta no eas.json (profile production).
echo Se pedir login: eas login
echo.
call eas build --platform android --profile production
if errorlevel 1 (
  echo.
  echo Build falhou. Veja a mensagem acima.
  pause
  exit /b 1
)
echo.
echo Download do .aab em: https://expo.dev
pause
