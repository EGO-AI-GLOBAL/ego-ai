@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.41
start "" notepad "%~dp0marketing\VALIDAR-1.0.41.txt"
echo Checklist 1.0.41 aberto.
pause
