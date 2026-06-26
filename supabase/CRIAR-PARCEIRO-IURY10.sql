-- EGO-AI — cupom IURY10 (cole no Supabase SQL Editor e RUN)

insert into public.referral_partners (code, display_name, contact_email, payout_pix, notes, active)
values (
  'IURY10',
  'Iury',
  null,
  null,
  'Cupom teste / fundador',
  true
)
on conflict (code) do update set
  display_name = excluded.display_name,
  notes = excluded.notes,
  active = true;

select code, display_name, active, created_at
from public.referral_partners
where upper(code) = 'IURY10';
