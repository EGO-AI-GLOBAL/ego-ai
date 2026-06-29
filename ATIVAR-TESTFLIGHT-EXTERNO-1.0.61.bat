@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TestFlight EXTERNO 1.0.61

echo.
echo ============================================================
echo   TestFlight EXTERNO — 1.0.61 build 50
echo ============================================================
echo.
echo Submit ja feito. Agora na App Store Connect:
echo   1. Build 50 ^> export compliance (criptografia: NAO)
echo   2. Testes EXTERNOS ^> seu grupo ^> + build 50
echo   3. Cola as notas de marketing\TESTFLIGHT-EXTERNO-1.0.61.txt
echo   4. Enviar para revisao beta
echo   5. Quando aprovar: MENSAGEM-TESTADORES-1.0.61.txt
echo.

start "" "https://appstoreconnect.apple.com/apps/6780595396/testflight/ios"
timeout /t 2 /nobreak >nul
notepad "marketing\TESTFLIGHT-EXTERNO-1.0.61.txt"
notepad "marketing\NOTAS-1.0.61-PLAY.txt"
notepad "marketing\MENSAGEM-TESTADORES-1.0.61.txt"

pause
