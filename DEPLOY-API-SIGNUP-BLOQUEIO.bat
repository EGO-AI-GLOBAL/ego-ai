@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API — bloqueio cadastro duplicado

echo.
echo [1/4] regression_guard
python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo [2/4] smoke_test_api
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo [3/4] commit + push Railway
git add ego_api/services.py ego_api/db.py scripts/regression_guard.py scripts/smoke_test_signup_duplicate.py flask_api.py DEPLOY-API-SIGNUP-BLOQUEIO.bat VERIFICAR-CADASTRO-DUPLICADO.bat

git diff --cached --quiet
if %errorlevel%==0 (
  echo Nada novo para commit — a fazer push na mesma...
  git push origin main
  goto :wait
)

git commit -m "fix: bloquear e-mail e telefone duplicados no cadastro"
if errorlevel 1 ( pause & exit /b 1 )

git push origin main
if errorlevel 1 ( pause & exit /b 1 )

:wait
echo.
echo [4/4] Aguardar Railway (~90s) e testar cadastro...
timeout /t 90 /nobreak >nul

python scripts\smoke_test_signup_duplicate.py
if errorlevel 1 (
  echo.
  echo Deploy pode ainda estar a propagar — corra VERIFICAR-CADASTRO-DUPLICADO.bat daqui a 1 min.
  pause
  exit /b 1
)

echo.
echo PRONTO — API no ar com bloqueio de cadastro duplicado.
pause
