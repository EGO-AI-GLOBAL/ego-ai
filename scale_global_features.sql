-- Supabase SQL Editor: tokens mensais no perfil + feedback nas respostas.
-- Ajuste chat_history se a sua tabela já tiver coluna `id` com outro tipo.

-- Perfis: uso mensal aproximado de tokens e período civil (YYYY-MM em UTC).
alter table public.profiles add column if not exists monthly_tokens_used bigint not null default 0;
alter table public.profiles add column if not exists monthly_tokens_period text default '';

-- Identificador estável por mensagem (evita conflito se já existir outra coluna `id`).
alter table public.chat_history add column if not exists ego_msg_id uuid default gen_random_uuid();
create unique index if not exists chat_history_ego_msg_uidx on public.chat_history (ego_msg_id);

-- Feedback 👍 / 👎 (chat_message_id em texto para compatibilidade com migrações antigas)
create table if not exists public.message_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  chat_message_id text,
  vote smallint not null check (vote in (1, -1)),
  model_provider text,
  created_at timestamptz not null default now()
);

create index if not exists message_feedback_user_idx on public.message_feedback (user_id);
create index if not exists message_feedback_msg_idx on public.message_feedback (chat_message_id);

alter table public.message_feedback enable row level security;

create policy "msg_feedback_select_own"
  on public.message_feedback for select
  using (auth.uid() = user_id);

create policy "msg_feedback_insert_own"
  on public.message_feedback for insert
  with check (auth.uid() = user_id);

create policy "msg_feedback_update_own"
  on public.message_feedback for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "msg_feedback_delete_own"
  on public.message_feedback for delete
  using (auth.uid() = user_id);
