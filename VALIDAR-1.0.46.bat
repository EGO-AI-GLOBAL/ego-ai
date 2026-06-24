@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.46

start "" notepad "%~dp0marketing\VALIDAR-1.0.46.txt"
echo Checklist 1.0.46 aberto.
pause
