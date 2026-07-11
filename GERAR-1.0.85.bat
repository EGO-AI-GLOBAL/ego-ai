@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.85 — iOS + Android

echo.
echo ============================================================
echo   EGO-AI 1.0.85 — sessão persiste após push + reset e-mail
echo ============================================================
echo   iOS 87 + Android 129 · submit iOS auto · Android manual
echo.

call _ego_run_python.bat scripts\onboarding_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.85.ids.json
if errorlevel 1 ( pause & exit /b 1 )

echo.
echo Depois: AGUARDAR-E-SUBMETER-1.0.85.bat
pause
