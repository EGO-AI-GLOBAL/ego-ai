-- Lista de compras: não apagar itens quando o compromisso é removido

alter table public.shopping_list_items
  drop constraint if exists shopping_list_items_reminder_id_fkey;

alter table public.shopping_list_items
  add constraint shopping_list_items_reminder_id_fkey
  foreign key (reminder_id) references public.reminders (id) on delete set null;
