@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Validar 1.0.38



start "" notepad "%~dp0marketing\VALIDAR-1.0.38.txt"

echo Abriu checklist 1.0.38 no Notepad.

pause
