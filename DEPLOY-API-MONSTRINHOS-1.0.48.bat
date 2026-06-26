@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deploy API — Monstrinhos F6 (1.0.48)

echo.
echo ============================================================
echo   DEPLOY API — 5 missões Monstrinhos (water + gratitude)
echo   Ficheiros: ego_api/daily_care.py + ego_api/config.py
echo ============================================================
echo.

python scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
python scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo A fazer commit+push (se ainda nao feito) e Railway faz deploy auto.
echo Se Railway nao ligado ao git: faz deploy manual no painel.
echo.
pause
