@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Validar 1.0.50

start "" notepad "%~dp0marketing\VALIDAR-1.0.50.txt"

echo Checklist 1.0.50 aberto — testar no iPhone antes de avisar testadores.

pause
