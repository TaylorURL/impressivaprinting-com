-- The same two staff emails the app used to seed into localStorage. Accounts
-- created with these addresses come up as admins; add a row to add an admin.
insert into public.admin_emails (email) values
  ('admin@impressivaprinting.com'),
  ('trenton@taylorurl.com')
on conflict do nothing;
