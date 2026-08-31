-- Default privileges hand EXECUTE on new functions to the API roles; take
-- it back everywhere it isn't needed. Trigger functions fire as the table
-- owner, so no API role ever needs to call them directly.

revoke execute on function public.handle_new_user() from public, anon, authenticated;
revoke execute on function public.guard_order_insert() from public, anon, authenticated;
revoke execute on function public.guard_order_update() from public, anon, authenticated;
revoke execute on function public.touch_order() from public, anon, authenticated;

-- Only signed-in users evaluate policies that ask about roles, and only
-- staff may remove customers; anon gets neither.
revoke execute on function public.is_admin() from anon;
revoke execute on function public.admin_remove_customer(uuid) from anon;

-- Platform helper that predates this schema; same hygiene.
do $$
begin
  if exists (
    select 1 from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public' and p.proname = 'rls_auto_enable'
  ) then
    revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
  end if;
end;
$$;
