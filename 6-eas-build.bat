@echo off

echo.

echo ============================================

echo   ATENCAO: use a pasta COPIA para o build

echo ============================================

echo.

echo O app Android completo esta em:

echo   EGO-AI-APP - Copia

echo.

echo Esta pasta (EGO-AI-APP) e o GitHub: API + SQL.

echo.

set /p GO="Abrir build na Copia agora? (S/N): "

if /I "%GO%"=="S" (

  cd /d "%~dp0..\EGO-AI-APP - Copia"

  call 6-eas-build.bat

) else (

  echo.

  echo Copie e cole no PowerShell:

  echo   cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia"

  echo   .\6-eas-build.bat

  pause

)

