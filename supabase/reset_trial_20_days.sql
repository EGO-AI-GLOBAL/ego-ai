-- Reinicia o trial de 20 dias para um e-mail (conta desde hoje em profiles.created_at).
-- Altere o e-mail abaixo → SQL Editor → Run → entre de novo na app.

update public.profiles
set created_at = now()
where email = 'teste@gmail.com';

-- Ver resultado:
select email, created_at, is_pro
from public.profiles
where email = 'teste@gmail.com';
