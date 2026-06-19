@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.33

echo CHECKLIST 1.0.33 (iOS build 16 / Android 65)
echo.
echo [ ] Conta mostra 1.0.33
echo [ ] Agenda - aba Entre Nos
echo [ ] Criar grupo + convidar 1 pessoa - push no celular B
echo [ ] Enviar convite compromisso - B confirma - A recebe push
echo [ ] Desabafo com parceiro - banner Entre Nos - Agendar
echo [ ] Chat: Desabafo agora + ofensiva
echo [ ] Railway EGO_LATEST_APP_VERSION=1.0.33 code 65
echo.
start "" notepad "%~dp0marketing\RELEASE-1.0.33.txt"
pause
