@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Validar 1.0.39



start "" notepad "%~dp0marketing\VALIDAR-1.0.39.txt"

echo Abriu checklist 1.0.39 no Notepad.

pause
