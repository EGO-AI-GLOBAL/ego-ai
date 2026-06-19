@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Validar 1.0.34

echo CHECKLIST 1.0.34 (iOS build 17 / Android 66)
echo.
echo [ ] Conta mostra 1.0.34
echo [ ] Aba Agenda compartilhada (nao Entre Nos no topo)
echo [ ] Cima: Familia / + Nova agenda compartilhada / Convidar / Novo compromisso
echo [ ] Baixo: Entre Nos — criar grupo aparece + Convidar parceiro(a)
echo [ ] Entre Nos: convite tarefa — Confirmar / Recusar nos 2 celulares
echo [ ] Desabafo agora — item Entre Nos
echo [ ] Chat texto + voz OK
echo [ ] Railway 1.0.34 code 66
echo.
start "" notepad "%~dp0marketing\RELEASE-1.0.34.txt"
pause
