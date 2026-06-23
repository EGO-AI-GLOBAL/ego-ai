@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Validar 1.0.40



start "" notepad "%~dp0marketing\VALIDAR-1.0.40.txt"

echo Abriu checklist 1.0.40 no Notepad.

pause
