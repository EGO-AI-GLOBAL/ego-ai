@echo off
chcp 65001 >nul
title EGO-AI — automatizar Firebase (1 login Google)
cd /d "%~dp0app"

echo.
echo === EGO Firebase automatico ===
echo 1) Vai abrir o browser para login Google (conta do EGO)
echo 2) Depois este script descarrega google-services.json + GoogleService-Info.plist
echo 3) AdMob units: Google NAO permite criar por CLI sem OAuth AdMob — usa o checklist
echo.

set NODE_TLS_REJECT_UNAUTHORIZED=0

echo A fazer login Firebase...
call npx --yes firebase-tools@13 login --no-localhost
if errorlevel 1 (
  echo LOGIN FALHOU.
  pause
  exit /b 1
)

echo.
echo Lista de projects:
call npx --yes firebase-tools@13 projects:list
echo.
set /p PID=Cola o Project ID do EGO (ex: ego-ai-xxxxx): 

if "%PID%"=="" (
  echo Sem project id.
  pause
  exit /b 1
)

call npx --yes firebase-tools@13 use "%PID%"
if errorlevel 1 (
  echo Project invalido. Cria em https://console.firebase.google.com com package com.egoai.app
  pause
  exit /b 1
)

echo.
echo A descarregar configs Android + iOS...
call npx --yes firebase-tools@13 apps:sdkconfig ANDROID --out google-services.json
call npx --yes firebase-tools@13 apps:sdkconfig IOS --out GoogleService-Info.plist

echo.
if exist google-services.json (echo OK google-services.json) else (echo FALTA google-services.json — cria app Android com.egoai.app no Firebase)
if exist GoogleService-Info.plist (echo OK GoogleService-Info.plist) else (echo FALTA GoogleService-Info.plist — cria app iOS com.egoai.app no Firebase)

echo.
echo Pronto Firebase. Volta ao Cursor e diz: firebase ok
echo AdMob: cria interstitial-pause-free + rewarded-dica-dia e cola os 4 IDs.
echo.
pause
