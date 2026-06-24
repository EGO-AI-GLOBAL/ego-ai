@echo off
set "SQL=%~dp0supabase\security_rls_hardening.sql"
start "" notepad "%SQL%"
echo.
echo 1. Abriu security_rls_hardening.sql
echo 2. Supabase -^> SQL Editor -^> cole tudo -^> Run
echo 3. Confirme rls_enabled = true em todas as tabelas listadas
echo.
pause
