@echo off

chcp 65001 >nul

cd /d "%~dp0"

title EGO-AI — testar relatório diário de cadastros

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0TESTAR-RELATORIO-CADASTROS.ps1"

pause

