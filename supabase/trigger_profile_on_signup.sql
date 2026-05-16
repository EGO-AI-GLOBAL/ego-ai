-- Executar no Supabase SQL Editor se profiles ficar vazio após cadastro.
-- Cria automaticamente uma linha em public.profiles quando alguém se regista no Auth.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, email, country, document_type)
  values (
    new.id,
    coalesce(
      nullif(trim(new.raw_user_meta_data->>'full_name'), ''),
      split_part(coalesce(new.email, ''), '@', 1),
      'Usuário'
    ),
    new.email,
    coalesce(nullif(trim(new.raw_user_meta_data->>'country'), ''), 'Brasil'),
    coalesce(new.raw_user_meta_data->>'document_type', '')
  )
  on conflict (id) do update set
    email = excluded.email,
    full_name = coalesce(nullif(excluded.full_name, ''), public.profiles.full_name);
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Utilizadores já existentes em Authentication sem linha em profiles:
insert into public.profiles (id, full_name, email, country, document_type)
select
  u.id,
  coalesce(nullif(trim(u.raw_user_meta_data->>'full_name'), ''), split_part(u.email, '@', 1), 'Usuário'),
  u.email,
  coalesce(nullif(trim(u.raw_user_meta_data->>'country'), ''), 'Brasil'),
  ''
from auth.users u
where not exists (select 1 from public.profiles p where p.id = u.id);
