@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Android 1.0.66 — enfileirar

echo.
echo ============================================================
echo   Android 1.0.66 — versionCode 106 (só Android)
echo ============================================================
echo.
echo Use se o GERAR-1.0.66 gerou iOS mas falhou no Android.
echo No fim: atualize builds-1.0.66.ids.json e rode AGUARDAR-E-SUBMETER-1.0.66.bat
echo.

call _ego_run_python.bat scripts\wait_and_submit_eas.py sync-check
if errorlevel 1 ( pause & exit /b 1 )

cd app
eas build --platform android --profile production --non-interactive --no-wait

echo.
echo Copie o build ID (UUID) da URL e grave em builds-1.0.66.ids.json no campo android.
pause
