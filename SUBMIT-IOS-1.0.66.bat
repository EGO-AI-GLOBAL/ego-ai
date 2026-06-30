@echo off
chcp 65001 >nul
cd /d "%~dp0\app"
title Submit iOS 1.0.66 — TestFlight

echo.
echo ============================================================
echo   Submit TestFlight 1.0.66 (build 40b6faa9...)
echo ============================================================
echo.
echo A build ja existe no EAS — isto envia para a Apple.
echo Depois: TestFlight no iPhone - Atualizar (15-60 min).
echo.

eas submit --platform ios --id 40b6faa9-1520-4e82-bafa-c62263b22c8b --non-interactive

echo.
pause
