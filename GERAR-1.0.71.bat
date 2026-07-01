@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar 1.0.71 — fix tela branca voz

call _ego_run_python.bat scripts\regression_guard.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\smoke_test_api.py
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )
call _ego_run_python.bat scripts\wait_and_submit_eas.py queue --ids-file builds-1.0.71.ids.json
if errorlevel 1 ( pause & exit /b 1 )
echo Depois: AGUARDAR-IOS-1.0.71.bat
pause
