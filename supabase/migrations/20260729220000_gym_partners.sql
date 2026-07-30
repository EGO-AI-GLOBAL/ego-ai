-- Academias parceiras (ShapeScan corpo + EGO mente) — separado de referral_partners (influencers).
-- Colar no SQL Editor do Supabase EGO se a migration automática não correr.

create table if not exists public.gym_partners (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  logo_url text,
  partner_code text not null,
  active boolean not null default true,
  cnpj text,
  razao_social text,
  endereco text,
  cidade text,
  uf text,
  cep text,
  email_oficial text,
  whatsapp text,
  representante_nome text,
  representante_cpf text,
  representante_cargo text,
  instagram text,
  login_email text,
  commission_pct integer not null default 30,
  stripe_connect_account_id text,
  source text not null default 'ego',
  products jsonb not null default '["ego"]'::jsonb,
  pitch text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint gym_partners_partner_code_unique unique (partner_code)
);

create index if not exists gym_partners_active_idx
  on public.gym_partners (active)
  where active = true;

create index if not exists gym_partners_cnpj_idx
  on public.gym_partners (cnpj)
  where cnpj is not null;

create table if not exists public.partner_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  login_email text not null,
  academia_nome text not null,
  razao_social text not null default '',
  cnpj text not null,
  endereco text not null default '',
  cidade text not null default '',
  uf text not null default '',
  cep text,
  email_oficial text not null default '',
  whatsapp text not null default '',
  representante_nome text not null default '',
  representante_cpf text not null default '',
  representante_cargo text,
  instagram text,
  partner_code text not null,
  status text not null default 'activated',
  auto_done jsonb not null default '[]'::jsonb,
  manual_todo jsonb not null default '[]'::jsonb,
  source text not null default 'ego',
  created_at timestamptz not null default now()
);

create index if not exists partner_applications_created_idx
  on public.partner_applications (created_at desc);

create index if not exists partner_applications_cnpj_idx
  on public.partner_applications (cnpj);

create index if not exists partner_applications_code_idx
  on public.partner_applications (partner_code);

alter table public.profiles
  add column if not exists gym_code text,
  add column if not exists must_change_password boolean not null default false;

create index if not exists profiles_gym_code_idx
  on public.profiles (gym_code)
  where gym_code is not null;

alter table public.gym_partners enable row level security;
alter table public.partner_applications enable row level security;

-- Sem políticas cliente: API usa service role (espelho ShapeScan / painel).

comment on table public.gym_partners is
  'Academias parceiras — Connect 30%; espelho ShapeScan (mesmo partner_code quando possível).';
comment on table public.partner_applications is
  'Candidatura academia (painel ou mirror ShapeScan).';
comment on column public.profiles.gym_code is
  'Código da academia (partner_code); aluno com gym_code → Stripe Connect, não IAP.';
comment on column public.profiles.must_change_password is
  '1.º acesso: aluno criado pela academia deve trocar a senha temp.';
