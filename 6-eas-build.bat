@echo off
cd /d "%~dp0app"
echo.
echo === Build Android production (.aab) - agenda compartilhada v1.0.3 ===
echo.
call eas env:create --name EXPO_PUBLIC_API_URL --value https://ego-ai-production-a2c2.up.railway.app --environment production --scope project --force --non-interactive
echo.
echo === Build production - pode demorar 20-40 min ===
call eas build --platform android --profile production --non-interactive
echo.
echo Download do .aab em: https://expo.dev
pause
