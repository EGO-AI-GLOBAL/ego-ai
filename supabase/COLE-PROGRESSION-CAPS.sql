-- Teto global de níveis/tiers (Desafio Diário + Jornada de Cuidado).
-- Começa em 500; a API acrescenta +500 quando alguém chega a cap-50 (450, 950…).

create table if not exists public.ego_progression_caps (
  key text primary key,
  cap integer not null default 500 check (cap >= 500),
  updated_at timestamptz not null default now()
);

insert into public.ego_progression_caps (key, cap)
values
  ('daily_care_tiers', 500),
  ('wellness_journey_levels', 500)
on conflict (key) do nothing;

alter table public.ego_progression_caps enable row level security;

-- Só service role escreve; leitura anónima opcional (API usa service role).
drop policy if exists "ego_progression_caps_read" on public.ego_progression_caps;
create policy "ego_progression_caps_read"
  on public.ego_progression_caps for select
  using (true);

drop policy if exists "ego_progression_caps_service" on public.ego_progression_caps;
create policy "ego_progression_caps_service"
  on public.ego_progression_caps for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
