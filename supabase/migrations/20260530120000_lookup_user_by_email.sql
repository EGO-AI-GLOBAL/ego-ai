-- Lookup de utilizador por e-mail (convites agenda compartilhada).
-- Usado pela API com service role: rpc('lookup_user_id_by_email', { p_email: '...' })

create or replace function public.lookup_user_id_by_email(p_email text)
returns uuid
language sql
stable
security definer
set search_path = public, auth
as $$
  select u.id
  from auth.users u
  where lower(trim(coalesce(u.email, ''))) = lower(trim(coalesce(p_email, '')))
  limit 1;
$$;

revoke all on function public.lookup_user_id_by_email(text) from public;
grant execute on function public.lookup_user_id_by_email(text) to service_role;
