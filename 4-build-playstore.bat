@echo off
cd /d "%~dp0app_local_backup"
echo.
echo === Ego-IA 1.0.5 ESTAVEL - build Play (.aab) - pasta app_local_backup ===
echo API: https://ego-ai-production-a2c2.up.railway.app
echo Package: com.egoai.app
echo.
echo 1) Faca: eas login   (5-eas-login.bat se precisar)
echo 2) Este script corre o build production...
echo.
pause
set NODE_TLS_REJECT_UNAUTHORIZED=0
set EAS_BUILD_NO_EXPO_GO_WARNING=true
call npx eas-cli build --platform android --profile production --non-interactive
echo.
echo Quando terminar: expo.dev -^> Builds -^> Download .aab
echo Play Console -^> Teste interno -^> Carregar .aab
pause
