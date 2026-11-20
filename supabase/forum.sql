-- Completed projects and the forum.
-- Run once in Supabase > SQL Editor. Safe to run again.
--
-- Completed projects are rows in public.posts with kind = 'write-up'; they appear
-- publicly once an admin sets status = 'published'.
-- Forum threads and comments are held for approval: they start as 'pending' and
-- appear publicly once an admin sets status = 'approved'. Authors always see their own.

-- 1. Extra project fields
alter table public.posts add column if not exists coauthors text;
alter table public.posts add column if not exists published_at timestamptz;
alter table public.posts add column if not exists author_notified_at timestamptz;

-- 2. Forum tables
create table if not exists public.threads (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null check (char_length(title) between 3 and 150),
  body text not null check (char_length(body) between 1 and 5000),
  status text not null default 'pending' check (status in ('pending', 'approved', 'hidden')),
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  notified_at timestamptz
);

create table if not exists public.comments (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  post_id bigint references public.posts(id) on delete cascade,
  thread_id bigint references public.threads(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 3000),
  status text not null default 'pending' check (status in ('pending', 'approved', 'hidden')),
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  notified_at timestamptz,
  constraint comment_has_one_target check ((post_id is null) <> (thread_id is null))
);
create index if not exists comments_post_idx on public.comments (post_id);
create index if not exists comments_thread_idx on public.comments (thread_id);

-- 3. Record when things are approved or published (used for emails and sorting)
create or replace function public.stamp_approved() returns trigger language plpgsql as $$
begin
  if new.status = 'approved' and old.status is distinct from 'approved' then new.approved_at := now(); end if;
  return new;
end $$;
drop trigger if exists threads_stamp on public.threads;
create trigger threads_stamp before update on public.threads for each row execute function public.stamp_approved();
drop trigger if exists comments_stamp on public.comments;
create trigger comments_stamp before update on public.comments for each row execute function public.stamp_approved();

create or replace function public.stamp_published() returns trigger language plpgsql as $$
begin
  if new.status = 'published' and old.status is distinct from 'published' then new.published_at := now(); end if;
  return new;
end $$;
drop trigger if exists posts_stamp on public.posts;
create trigger posts_stamp before update on public.posts for each row execute function public.stamp_published();

-- 4. The name shown publicly, following each person's own choice on their account
create or replace function public.display_name(uid uuid) returns text
language sql stable security definer set search_path = public as $$
  select coalesce((
    select case pr.name_visibility
      when 'full' then nullif(trim(pr.full_name), '')
      when 'first' then nullif(split_part(trim(pr.full_name), ' ', 1), '')
      else null end
    from public.profiles pr where pr.id = uid), 'A member');
$$;
revoke execute on function public.display_name(uuid) from public, anon, authenticated;

create or replace function public.is_published_project(pid bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.posts where id = pid and status = 'published' and kind = 'write-up');
$$;

-- 5. Who can do what
alter table public.threads enable row level security;
alter table public.comments enable row level security;

drop policy if exists "threads read" on public.threads;
create policy "threads read" on public.threads for select
  using (status = 'approved' or user_id = auth.uid() or public.is_admin());
drop policy if exists "threads insert own" on public.threads;
create policy "threads insert own" on public.threads for insert
  with check (auth.uid() is not null and user_id = auth.uid() and status = 'pending');
drop policy if exists "threads admin update" on public.threads;
create policy "threads admin update" on public.threads for update using (public.is_admin());
drop policy if exists "threads delete own or admin" on public.threads;
create policy "threads delete own or admin" on public.threads for delete
  using (user_id = auth.uid() or public.is_admin());

drop policy if exists "comments read" on public.comments;
create policy "comments read" on public.comments for select
  using (status = 'approved' or user_id = auth.uid() or public.is_admin());
drop policy if exists "comments insert own" on public.comments;
create policy "comments insert own" on public.comments for insert
  with check (auth.uid() is not null and user_id = auth.uid() and status = 'pending' and (
    (post_id is not null and public.is_published_project(post_id)) or
    (thread_id is not null and exists (select 1 from public.threads t where t.id = thread_id and t.status = 'approved'))));
drop policy if exists "comments admin update" on public.comments;
create policy "comments admin update" on public.comments for update using (public.is_admin());
drop policy if exists "comments delete own or admin" on public.comments;
create policy "comments delete own or admin" on public.comments for delete
  using (user_id = auth.uid() or public.is_admin());

-- 6. Public reading (no sign-in needed). These only ever return approved or published items.
create or replace function public.completed_projects()
returns table (id bigint, title text, summary text, link text, coauthors text, author text,
               question_id text, published_at timestamptz, comments bigint)
language sql stable security definer set search_path = public as $$
  select p.id, p.title, p.body, p.link, p.coauthors, public.display_name(p.user_id), t.question_id,
         coalesce(p.published_at, p.created_at),
         (select count(*) from public.comments c where c.post_id = p.id and c.status = 'approved')
  from public.posts p left join public.teams t on t.id = p.team_id
  where p.status = 'published' and p.kind = 'write-up'
  order by coalesce(p.published_at, p.created_at) desc;
$$;

create or replace function public.forum_threads()
returns table (id bigint, title text, author text, created_at timestamptz, replies bigint, last_activity timestamptz)
language sql stable security definer set search_path = public as $$
  select t.id, t.title, public.display_name(t.user_id), t.created_at,
         (select count(*) from public.comments c where c.thread_id = t.id and c.status = 'approved'),
         greatest(coalesce(t.approved_at, t.created_at),
                  coalesce((select max(c.approved_at) from public.comments c where c.thread_id = t.id and c.status = 'approved'), t.created_at))
  from public.threads t where t.status = 'approved'
  order by 6 desc;
$$;

create or replace function public.forum_thread(tid bigint)
returns table (id bigint, title text, body text, author text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select t.id, t.title, t.body, public.display_name(t.user_id), t.created_at
  from public.threads t where t.id = tid and t.status = 'approved';
$$;

create or replace function public.public_comments(pid bigint default null, tid bigint default null)
returns table (id bigint, body text, author text, created_at timestamptz)
language sql stable security definer set search_path = public as $$
  select c.id, c.body, public.display_name(c.user_id), c.created_at
  from public.comments c
  where c.status = 'approved'
    and ((pid is not null and c.post_id = pid and public.is_published_project(pid))
      or (tid is not null and c.thread_id = tid
          and exists (select 1 from public.threads t where t.id = tid and t.status = 'approved')))
  order by c.created_at;
$$;

grant execute on function public.completed_projects() to anon, authenticated;
grant execute on function public.forum_threads() to anon, authenticated;
grant execute on function public.forum_thread(bigint) to anon, authenticated;
grant execute on function public.public_comments(bigint, bigint) to anon, authenticated;
grant execute on function public.is_published_project(bigint) to anon, authenticated;
grant select, insert, delete on public.threads, public.comments to authenticated;
grant update on public.threads, public.comments to authenticated;
grant select on public.threads, public.comments to anon;

select 'ok' as result;
