-- Se aparecer erro de "tamanho" / "too long" ao gravar e-mail no perfil:
-- alarga colunas para text (sem limite prático).

alter table public.profiles alter column email type text;
alter table public.profiles alter column full_name type text;
alter table public.profiles alter column country type text;
alter table public.profiles alter column document_type type text;
