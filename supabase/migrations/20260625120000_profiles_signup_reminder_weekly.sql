-- Lembretes semanais: quem cadastrou e não fez login (até 4 lembretes após boas-vindas).

alter table public.profiles
  add column if not exists signup_reminder_count integer not null default 0;

comment on column public.profiles.signup_reminder_count is
  'Quantos lembretes pós-cadastro já foram enviados (sem login). Máx. 4.';

-- Quem já recebeu o lembrete único antigo conta como 1.
update public.profiles
set signup_reminder_count = 1
where signup_reminder_sent_at is not null
  and coalesce(signup_reminder_count, 0) = 0;

drop index if exists public.profiles_signup_reminder_idx;
drop index if exists public.profiles_signup_reminder_pending_idx;

create index if not exists profiles_signup_reminder_weekly_idx
  on public.profiles (created_at desc)
  where welcome_email_sent_at is not null
    and last_login_at is null
    and coalesce(signup_reminder_count, 0) < 4;
