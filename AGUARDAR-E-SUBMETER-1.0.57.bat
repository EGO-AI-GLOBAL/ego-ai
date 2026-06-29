@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Aguardar e submeter 1.0.57

python scripts\wait_and_submit_eas.py wait-submit --ids-file builds-1.0.57.ids.json

pause
