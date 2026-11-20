-- Run once in Supabase > SQL Editor (20 Nov 2026), after forum.sql.
-- Forum threads, replies and comments on listed projects now go live straight away.
-- Admins remove anything unsuitable from admin.html (it sets status = 'hidden').

-- Threads: signed-in people start their own, live at once.
drop policy if exists "threads insert own" on public.threads;
create policy "threads insert own" on public.threads for insert
  with check (auth.uid() is not null and user_id = auth.uid() and status = 'approved');

-- Comments: signed-in people post their own, live at once, on a listed project or a live thread.
drop policy if exists "comments insert own" on public.comments;
create policy "comments insert own" on public.comments for insert
  with check (auth.uid() is not null and user_id = auth.uid() and status = 'approved' and (
    (post_id is not null and thread_id is null and public.is_published_project(post_id)) or
    (thread_id is not null and post_id is null and exists (select 1 from public.threads t where t.id = thread_id and t.status = 'approved'))));

-- Stamp approved_at when something is posted live, so the hourly job still emails the author it replies to.
create or replace function public.stamp_approved_on_insert() returns trigger language plpgsql as $$
begin
  if new.status = 'approved' then new.approved_at := now(); end if;
  return new;
end $$;
drop trigger if exists threads_stamp_insert on public.threads;
create trigger threads_stamp_insert before insert on public.threads
  for each row execute function public.stamp_approved_on_insert();
drop trigger if exists comments_stamp_insert on public.comments;
create trigger comments_stamp_insert before insert on public.comments
  for each row execute function public.stamp_approved_on_insert();

-- Make Zebedi's own account an admin, so he can moderate without the shared Gmail.
insert into public.admins (user_id)
select id from auth.users where email = 'zwc22@cam.ac.uk'
on conflict do nothing;
