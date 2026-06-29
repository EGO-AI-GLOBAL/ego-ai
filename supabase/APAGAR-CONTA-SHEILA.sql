-- EGO-AI — Apagar conta para cadastro novo
-- Supabase → SQL Editor → cole TUDO → RUN
-- E-mail: kta.sheila28@gmail.com (prima / testadora Android)

-- Ver se existe antes
SELECT id, email, created_at
FROM auth.users
WHERE lower(trim(email)) = lower(trim('kta.sheila28@gmail.com'));

-- Apagar (remove perfil, chat, agenda, etc. em cascade)
DELETE FROM auth.users
WHERE lower(trim(email)) = lower(trim('kta.sheila28@gmail.com'));

-- Confirmar que sumiu (deve voltar 0 linhas)
SELECT id, email
FROM auth.users
WHERE lower(trim(email)) = lower(trim('kta.sheila28@gmail.com'));

SELECT id, email
FROM public.profiles
WHERE lower(trim(email)) = lower(trim('kta.sheila28@gmail.com'));

-- Depois: Sheila abre o app → Cadastrar → mesmo e-mail → escolhe Luna → «oi» no chat.
