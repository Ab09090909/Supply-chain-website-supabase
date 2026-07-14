-- ============================================================================
-- FIX: "Database error saving new user" — Run this NOW in Supabase SQL Editor
-- ----------------------------------------------------------------------------
-- This is a standalone fix. You don't need to re-run schema.sql.
-- It does 3 things:
--   1. Drops and recreates the handle_new_user trigger function WITH
--      `set search_path = public` (the missing line that was breaking signup).
--   2. Re-attaches the trigger to auth.users.
--   3. Backfills profiles for any auth.users that were created without one
--      (i.e. the failed signups from before this fix).
--
-- After running this, try signing up again — it should work.
-- ============================================================================

-- --------------------------------------------------------------------------
-- STEP 1: Recreate the trigger function (with the search_path fix + safety net)
-- --------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  begin
    insert into public.profiles (id, email, full_name, role, phone, location, company)
    values (
      new.id,
      new.email,
      coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
      coalesce((new.raw_user_meta_data->>'role')::user_role, 'customer'::user_role),
      new.raw_user_meta_data->>'phone',
      new.raw_user_meta_data->>'location',
      new.raw_user_meta_data->>'company'
    )
    on conflict (id) do nothing;
  exception when others then
    -- Log the error but DO NOT fail the auth insert
    raise warning 'handle_new_user: profile insert failed for user % (%): %',
      new.id, new.email, sqlerrm;
  end;
  return new;
end;
$$;

-- --------------------------------------------------------------------------
-- STEP 2: Re-attach the trigger (drop old, create new)
-- --------------------------------------------------------------------------
drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- --------------------------------------------------------------------------
-- STEP 3: Backfill profiles for orphaned auth users
-- (anyone who signed up before this fix and got rolled back, or whose trigger
--  silently failed — they'll have an auth.users row but no profiles row)
-- --------------------------------------------------------------------------
insert into public.profiles (id, email, full_name, role, phone, location, company)
select
  u.id,
  u.email,
  coalesce(u.raw_user_meta_data->>'full_name', split_part(u.email, '@', 1)),
  coalesce((u.raw_user_meta_data->>'role')::user_role, 'customer'::user_role),
  u.raw_user_meta_data->>'phone',
  u.raw_user_meta_data->>'location',
  u.raw_user_meta_data->>'company'
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null
on conflict (id) do nothing;

-- --------------------------------------------------------------------------
-- STEP 4: Diagnostic — show the result
-- --------------------------------------------------------------------------
select
  (select count(*) from auth.users)                                    as auth_user_count,
  (select count(*) from public.profiles)                               as profile_count,
  (select count(*)
   from auth.users u
   left join public.profiles p on p.id = u.id
   where p.id is null)                                                 as orphaned_users;

-- Expected: orphaned_users = 0 after running this.
-- If auth_user_count > 0 and profile_count = 0, something else is wrong —
-- check the Postgres logs in Supabase Dashboard > Logs > Postgres.
