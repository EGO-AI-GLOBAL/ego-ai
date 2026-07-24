@echo off
setlocal
cd /d "%~dp0"
echo.
echo === Verificar metadados Stripe (planos equipe 100 lugares) ===
echo.
if not exist ".venv\Scripts\python.exe" (
  py -3.12 scripts\verify_stripe_team_100_metadata.py
) else (
  .venv\Scripts\python.exe scripts\verify_stripe_team_100_metadata.py
)
echo.
pause
