-- Permite ao criador da agenda actualizar membros (convites pendentes, reactivação).

drop policy if exists "shared_members_update_owner" on public.shared_calendar_members;
create policy "shared_members_update_owner"
  on public.shared_calendar_members for update
  using (public.is_shared_calendar_owner(calendar_id))
  with check (public.is_shared_calendar_owner(calendar_id));
