-- Supabase → SQL Editor → New query → cole, altere os 3 valores abaixo → Run.
-- Cria utilizador de teste com login por e-mail/senha (sem enviar e-mail).
-- Requer: extensão pgcrypto + tabela public.profiles (bootstrap_ego_schema.sql).

create extension if not exists pgcrypto;

do $$
declare
  -- ========== ALTERE AQUI ==========
  v_email text := 'teste@egoai.com';
  v_password text := 'Teste123456';
  v_nome text := 'Usuario Teste';
  -- =================================

  v_user_id uuid := gen_random_uuid();
  v_encrypted_pw text := crypt(v_password, gen_salt('bf'));
begin
  if exists (select 1 from auth.users where email = v_email) then
    raise exception 'E-mail já existe: %. Use outro ou apague em Authentication → Users.', v_email;
  end if;

  insert into auth.users (
    id,
    instance_id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    confirmation_sent_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at
  )
  values (
    v_user_id,
    '00000000-0000-0000-0000-000000000000',
    'authenticated',
    'authenticated',
    v_email,
    v_encrypted_pw,
    now(),
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    jsonb_build_object('full_name', v_nome, 'country', 'Brasil'),
    now(),
    now()
  );

  insert into auth.identities (
    id,
    user_id,
    identity_data,
    provider,
    provider_id,
    last_sign_in_at,
    created_at,
    updated_at
  )
  values (
    v_user_id,
    v_user_id,
    jsonb_build_object('sub', v_user_id::text, 'email', v_email),
    'email',
    v_user_id::text,
    now(),
    now(),
    now()
  );

  insert into public.profiles (id, full_name, email, country, document_type, created_at)
  values (v_user_id, v_nome, v_email, 'Brasil', '', now())
  on conflict (id) do update set
    full_name = excluded.full_name,
    email = excluded.email,
    created_at = coalesce(public.profiles.created_at, excluded.created_at, now());

  raise notice 'OK — user_id: % | email: % | senha: (a que definiu acima)', v_user_id, v_email;
end $$;
