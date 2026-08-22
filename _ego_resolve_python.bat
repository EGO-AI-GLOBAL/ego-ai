@echo off
REM Define EGO_PY (caminho) ou EGO_PY=py + EGO_PY_ARGS=-3 — evita alias da Microsoft Store.
set "EGO_PY="
set "EGO_PY_ARGS="
if exist "%~dp0.venv\Scripts\python.exe" (
  set "EGO_PY=%~dp0.venv\Scripts\python.exe"
  goto :ok
)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
  set "EGO_PY=%LOCALAPPDATA%\Python\bin\python.exe"
  goto :ok
)
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "EGO_PY=py"
  set "EGO_PY_ARGS=-3"
  goto :ok
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "EGO_PY=python"
  goto :ok
)
echo ERRO: Python nao encontrado.
echo Instale em https://www.python.org/downloads/ ou desative o alias
echo "python.exe" em Configuracoes ^> Aplicativos ^> Aliases de execucao.
exit /b 1
:ok
exit /b 0
