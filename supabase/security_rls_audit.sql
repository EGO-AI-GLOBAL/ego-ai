-- Auditoria rápida de RLS/policies das tabelas usadas pelo EGO-AI.
-- Execute no SQL Editor do Supabase.

select
  n.nspname as schema_name,
  c.relname as table_name,
  c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'profiles',
    'chat_history',
    'user_personas',
    'agenda',
    'reminders',
    'message_feedback'
  )
order by c.relname;

select
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
from pg_policies
where schemaname = 'public'
  and tablename in (
    'profiles',
    'chat_history',
    'user_personas',
    'agenda',
    'reminders',
    'message_feedback'
  )
order by tablename, cmd, policyname;

