-- ============================================================================
-- AI Supply Chain Platform — v5 Migration
-- ----------------------------------------------------------------------------
-- Adds:
--   1. verification_documents table (national ID, license, business permit)
--   2. verification_status column on profiles (pending/verified/rejected)
--   3. admin_activity_logs table (audit trail for admin actions)
-- ============================================================================

-- --------------------------------------------------------------------------
-- 1. Add verification_status to profiles
-- --------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='verification_status') then
    alter table public.profiles add column verification_status text not null default 'pending' check (verification_status in ('pending', 'verified', 'rejected'));
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='verification_submitted_at') then
    alter table public.profiles add column verification_submitted_at timestamptz;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='verification_reviewed_at') then
    alter table public.profiles add column verification_reviewed_at timestamptz;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='profiles' and column_name='verification_notes') then
    alter table public.profiles add column verification_notes text;
  end if;
end $$;

-- --------------------------------------------------------------------------
-- 2. VERIFICATION_DOCUMENTS table
-- --------------------------------------------------------------------------
create table if not exists public.verification_documents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles (id) on delete cascade,
  document_type   text not null check (document_type in ('national_id', 'drivers_license', 'passport', 'business_license', 'tax_certificate', 'other')),
  document_number text,
  document_name   text not null,
  file_url        text not null,
  file_size       integer,
  mime_type       text,
  status          text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  uploaded_at     timestamptz not null default now(),
  reviewed_by     uuid references public.profiles (id) on delete set null,
  reviewed_at     timestamptz,
  review_notes    text
);

create index if not exists idx_verif_docs_user on public.verification_documents (user_id);
create index if not exists idx_verif_docs_status on public.verification_documents (status);

alter table public.verification_documents enable row level security;

create policy "Users can view own verification docs"
  on public.verification_documents for select
  using (auth.uid() = user_id or public.is_admin());

create policy "Users can upload own verification docs"
  on public.verification_documents for insert
  with check (auth.uid() = user_id);

create policy "Users can update own pending docs"
  on public.verification_documents for update
  using (auth.uid() = user_id or public.is_admin());

create policy "Admins can delete any verification doc"
  on public.verification_documents for delete
  using (public.is_admin());

-- Storage bucket for verification documents (private)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'verification-docs',
  'verification-docs',
  false,
  10485760,
  array['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
)
on conflict (id) do nothing;

drop policy if exists "Users can upload own verification docs to storage" on storage.objects;
create policy "Users can upload own verification docs to storage"
  on storage.objects for insert
  with check (
    bucket_id = 'verification-docs'
    and auth.role() = 'authenticated'
  );

drop policy if exists "Users can view own verification docs in storage" on storage.objects;
create policy "Users can view own verification docs in storage"
  on storage.objects for select
  using (
    bucket_id = 'verification-docs'
    and (auth.role() = 'authenticated')
  );

drop policy if exists "Admins can view all verification docs" on storage.objects;
create policy "Admins can view all verification docs"
  on storage.objects for select
  using (
    bucket_id = 'verification-docs'
    and public.is_admin()
  );

-- --------------------------------------------------------------------------
-- 3. ADMIN_ACTIVITY_LOGS table (audit trail)
-- --------------------------------------------------------------------------
create table if not exists public.admin_activity_logs (
  id          uuid primary key default gen_random_uuid(),
  admin_id    uuid not null references public.profiles (id) on delete cascade,
  action      text not null,
  target_table text,
  target_id   text,
  details     jsonb default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index if not exists idx_admin_logs_admin on public.admin_activity_logs (admin_id);
create index if not exists idx_admin_logs_created on public.admin_activity_logs (created_at desc);

alter table public.admin_activity_logs enable row level security;

create policy "Admins can view activity logs"
  on public.admin_activity_logs for select
  using (public.is_admin());

create policy "Admins can insert activity logs"
  on public.admin_activity_logs for insert
  with check (public.is_admin());

-- --------------------------------------------------------------------------
-- 4. Mark existing verified profiles
-- --------------------------------------------------------------------------
update public.profiles set verification_status = 'verified' where is_verified = true and verification_status = 'pending';

select 'v5 migration complete: verification_documents table + admin_activity_logs table + verification_status column on profiles.' as result;
