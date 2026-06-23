@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.42
start "" notepad "%~dp0marketing\VALIDAR-1.0.42.txt"
echo Checklist 1.0.42 aberto.
pause
