@echo off

chcp 65001 >nul

cd /d "%~dp0"

title Submeter iOS 1.0.50 — TestFlight

echo.
echo Use AGUARDAR-E-SUBMETER-1.0.50.bat — espera iOS+Android e sobe os dois UMA vez.
echo.

call "%~dp0AGUARDAR-E-SUBMETER-1.0.50.bat"
