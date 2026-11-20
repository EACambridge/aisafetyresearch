-- Run once in Supabase > SQL Editor (20 Nov 2026), after forum.sql.
-- Comments on listed projects now go live straight away; admins can hide them.
-- The forum's threads page is gone, so nobody can start new threads.

-- Comments: signed-in people post their own, live at once, only on listed projects.
drop policy if exists "comments insert own" on public.comments;
create policy "comments insert own" on public.comments for insert
  with check (auth.uid() is not null and user_id = auth.uid() and status = 'approved'
              and thread_id is null and post_id is not null and public.is_published_project(post_id));

-- Stamp approved_at when a comment is created live, so the hourly job still emails the project's author.
create or replace function public.stamp_approved_on_insert() returns trigger language plpgsql as $$
begin
  if new.status = 'approved' then new.approved_at := now(); end if;
  return new;
end $$;
drop trigger if exists comments_stamp_insert on public.comments;
create trigger comments_stamp_insert before insert on public.comments
  for each row execute function public.stamp_approved_on_insert();

-- No new threads.
drop policy if exists "threads insert own" on public.threads;

-- Make Zebedi's own account an admin, so he can moderate without the shared Gmail.
insert into public.admins (user_id)
select id from auth.users where email = 'zwc22@cam.ac.uk'
on conflict do nothing;
