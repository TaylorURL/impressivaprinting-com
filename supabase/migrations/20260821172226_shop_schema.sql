-- Impressiva Printing shop schema: accounts, orders, artwork, and the
-- policies that keep customers inside their own data.

-- ---- profiles --------------------------------------------------------------
-- One row per auth user. Created by trigger on signup; role comes from the
-- admin_emails allowlist so staff accounts never rely on a shipped password.

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  name text not null default '',
  role text not null default 'customer' check (role in ('customer', 'admin')),
  company text not null default '',
  phone text not null default '',
  created_at timestamptz not null default now()
);

-- Emails on this list become admins when their account is created. Locked
-- down: no API policies, only definer functions read it.
create table public.admin_emails (
  email text primary key
);

-- Internal shop notes about a customer. Separate from profiles so customers
-- can never read or write what staff keep about them.
create table public.customer_notes (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  note text not null default ''
);

-- ---- orders ----------------------------------------------------------------

-- Order numbers start above 1000 so the shop reads as established, not empty.
create sequence public.order_number_seq start 1042;

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  number text not null unique default 'IMP-' || nextval('public.order_number_seq'),
  user_id uuid not null references public.profiles (id) on delete cascade,
  product jsonb not null,
  qty integer check (qty is null or qty > 0),
  size text not null default '',
  finish text not null default '',
  due_date text not null default '',
  notes text not null default '',
  status text not null default 'awaiting-artwork' check (
    status in ('awaiting-artwork', 'in-review', 'proofing', 'in-production', 'ready', 'completed', 'canceled')
  ),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index orders_user_id_idx on public.orders (user_id);

create table public.order_events (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id) on delete cascade,
  actor text not null check (actor in ('customer', 'shop')),
  kind text not null,
  label text not null,
  note text not null default '',
  at timestamptz not null default now()
);

create index order_events_order_id_idx on public.order_events (order_id, at);

-- Artwork and proofs ride along as data URLs (the app caps files at 4 MB).
-- List queries skip data_url; only the order detail view pulls it.
create table public.order_files (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders (id) on delete cascade,
  file_name text not null,
  file_type text not null default '',
  size integer,
  data_url text not null,
  uploaded_by text not null default 'customer' check (uploaded_by in ('customer', 'shop')),
  uploaded_at timestamptz not null default now()
);

create index order_files_order_id_idx on public.order_files (order_id);

-- ---- helpers ---------------------------------------------------------------

-- Security definer so policies on profiles can ask about the caller's role
-- without recursing into profiles' own policies.
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = (select auth.uid()) and role = 'admin'
  );
$$;

revoke execute on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;

-- Every new auth user gets a profile; the allowlist decides the role.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, name, role, company, phone)
  values (
    new.id,
    new.email,
    coalesce(nullif(trim(new.raw_user_meta_data ->> 'name'), ''), split_part(new.email, '@', 1)),
    case
      when exists (select 1 from public.admin_emails where lower(email) = lower(new.email)) then 'admin'
      else 'customer'
    end,
    coalesce(new.raw_user_meta_data ->> 'company', ''),
    coalesce(new.raw_user_meta_data ->> 'phone', '')
  );
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- New orders can only enter the pipeline at the artwork stage.
create or replace function public.guard_order_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.is_admin() and new.status not in ('awaiting-artwork', 'in-review') then
    raise exception 'New orders start in the artwork stage.';
  end if;
  return new;
end;
$$;

create trigger orders_guard_insert
before insert on public.orders
for each row execute function public.guard_order_insert();

-- Customers only get the moves the portal offers: upload art, cancel early,
-- pull the last file, answer a proof. updated_at is server-set either way.
create or replace function public.guard_order_update()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.updated_at := now();
  if new.status is distinct from old.status and not public.is_admin() then
    if not (
      (old.status = 'awaiting-artwork' and new.status in ('in-review', 'canceled'))
      or (old.status = 'in-review' and new.status = 'awaiting-artwork')
      or (old.status = 'proofing' and new.status in ('in-production', 'in-review'))
    ) then
      raise exception 'That status change is the shop''s to make.';
    end if;
  end if;
  return new;
end;
$$;

create trigger orders_guard_update
before update on public.orders
for each row execute function public.guard_order_update();

-- Notes and files count as activity on the order.
create or replace function public.touch_order()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.orders set updated_at = now()
  where id = coalesce(new.order_id, old.order_id);
  return coalesce(new, old);
end;
$$;

create trigger order_events_touch
after insert on public.order_events
for each row execute function public.touch_order();

create trigger order_files_touch
after insert or delete on public.order_files
for each row execute function public.touch_order();

-- Removing a customer takes their auth account, profile, orders and files
-- with them, and is refused for staff. The definer runs as the table owner,
-- which is what allows the auth.users delete.
create or replace function public.admin_remove_customer(target uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Only staff can remove customers.';
  end if;
  if not exists (select 1 from public.profiles where id = target and role = 'customer') then
    raise exception 'That account is not a removable customer.';
  end if;
  delete from auth.users where id = target;
end;
$$;

revoke execute on function public.admin_remove_customer(uuid) from public;
grant execute on function public.admin_remove_customer(uuid) to authenticated;

-- ---- privileges ------------------------------------------------------------
-- Start from nothing, then grant only what the app actually does. Column
-- lists keep role, email, order numbers and timestamps server-owned.

revoke all on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (name, company, phone) on public.profiles to authenticated;

revoke all on public.admin_emails from anon, authenticated;

revoke all on public.customer_notes from anon, authenticated;
grant select on public.customer_notes to authenticated;
grant insert (user_id, note) on public.customer_notes to authenticated;
grant update (note) on public.customer_notes to authenticated;
grant delete on public.customer_notes to authenticated;

revoke all on public.orders from anon, authenticated;
grant select on public.orders to authenticated;
grant insert (user_id, product, qty, size, finish, due_date, notes, status) on public.orders to authenticated;
grant update (status) on public.orders to authenticated;
grant delete on public.orders to authenticated;
grant usage on sequence public.order_number_seq to authenticated;

revoke all on public.order_events from anon, authenticated;
grant select on public.order_events to authenticated;
grant insert (order_id, actor, kind, label, note) on public.order_events to authenticated;

revoke all on public.order_files from anon, authenticated;
grant select on public.order_files to authenticated;
grant insert (order_id, file_name, file_type, size, data_url, uploaded_by) on public.order_files to authenticated;
grant delete on public.order_files to authenticated;

-- ---- row level security ----------------------------------------------------

alter table public.profiles enable row level security;
alter table public.admin_emails enable row level security;
alter table public.customer_notes enable row level security;
alter table public.orders enable row level security;
alter table public.order_events enable row level security;
alter table public.order_files enable row level security;

create policy "profiles: own row or staff" on public.profiles
  for select to authenticated
  using (id = (select auth.uid()) or public.is_admin());

create policy "profiles: edit own row or staff" on public.profiles
  for update to authenticated
  using (id = (select auth.uid()) or public.is_admin())
  with check (id = (select auth.uid()) or public.is_admin());

create policy "customer notes: staff only" on public.customer_notes
  for all to authenticated
  using (public.is_admin())
  with check (public.is_admin());

create policy "orders: own or staff" on public.orders
  for select to authenticated
  using (user_id = (select auth.uid()) or public.is_admin());

create policy "orders: customers place their own" on public.orders
  for insert to authenticated
  with check (user_id = (select auth.uid()) or public.is_admin());

create policy "orders: update own or staff" on public.orders
  for update to authenticated
  using (user_id = (select auth.uid()) or public.is_admin())
  with check (user_id = (select auth.uid()) or public.is_admin());

create policy "orders: staff delete" on public.orders
  for delete to authenticated
  using (public.is_admin());

create policy "order events: visible with the order" on public.order_events
  for select to authenticated
  using (
    public.is_admin()
    or exists (
      select 1 from public.orders o
      where o.id = order_id and o.user_id = (select auth.uid())
    )
  );

create policy "order events: written by their actor" on public.order_events
  for insert to authenticated
  with check (
    (public.is_admin() and actor = 'shop')
    or (
      actor = 'customer'
      and exists (
        select 1 from public.orders o
        where o.id = order_id and o.user_id = (select auth.uid())
      )
    )
  );

create policy "order files: visible with the order" on public.order_files
  for select to authenticated
  using (
    public.is_admin()
    or exists (
      select 1 from public.orders o
      where o.id = order_id and o.user_id = (select auth.uid())
    )
  );

create policy "order files: added by their uploader" on public.order_files
  for insert to authenticated
  with check (
    (public.is_admin() and uploaded_by = 'shop')
    or (
      uploaded_by = 'customer'
      and exists (
        select 1 from public.orders o
        where o.id = order_id and o.user_id = (select auth.uid())
      )
    )
  );

create policy "order files: customers pull artwork while editable, staff always" on public.order_files
  for delete to authenticated
  using (
    public.is_admin()
    or (
      uploaded_by = 'customer'
      and exists (
        select 1 from public.orders o
        where o.id = order_id
          and o.user_id = (select auth.uid())
          and o.status in ('awaiting-artwork', 'in-review')
      )
    )
  );
