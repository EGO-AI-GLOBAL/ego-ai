@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TestFlight EXTERNO 1.0.60

echo.
echo ============================================================
echo   TestFlight EXTERNO — 1.0.60 build 47
echo ============================================================
echo.
echo Submit ja feito. Agora na App Store Connect:
echo   1. Build 47 ^> export compliance (criptografia: NAO)
echo   2. Testes EXTERNOS ^> seu grupo ^> + build 47
echo   3. Cola as notas de marketing\TESTFLIGHT-EXTERNO-1.0.60.txt
echo   4. Enviar para revisao beta
echo   5. Quando aprovar: MENSAGEM-TESTADORES-1.0.60.txt
echo.

start "" "https://appstoreconnect.apple.com/apps/6780595396/testflight/ios"
timeout /t 2 /nobreak >nul
notepad "marketing\TESTFLIGHT-EXTERNO-1.0.60.txt"
notepad "marketing\NOTAS-1.0.60-PLAY.txt"
notepad "marketing\MENSAGEM-TESTADORES-1.0.60.txt"

pause
