@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.47

start "" notepad "%~dp0marketing\VALIDAR-1.0.47.txt"
echo Checklist 1.0.47 aberto.
pause
