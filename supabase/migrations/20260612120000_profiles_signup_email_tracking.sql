-- Rastreio de e-mails automáticos pós-cadastro (boas-vindas + lembrete 24h).

alter table public.profiles
  add column if not exists welcome_email_sent_at timestamptz,
  add column if not exists signup_reminder_sent_at timestamptz;

create index if not exists profiles_signup_reminder_idx
  on public.profiles (created_at)
  where welcome_email_sent_at is not null
    and signup_reminder_sent_at is null
    and last_login_at is null;
