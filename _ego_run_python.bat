@echo off
REM Uso: call _ego_run_python.bat scripts\regression_guard.py [args...]
call "%~dp0_ego_resolve_python.bat"
if errorlevel 1 exit /b 1
if defined EGO_PY_ARGS (
  %EGO_PY% %EGO_PY_ARGS% %*
) else (
  "%EGO_PY%" %*
)
exit /b %ERRORLEVEL%
