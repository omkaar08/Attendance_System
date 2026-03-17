-- Synchronize auth.users into public.users and enable row-level security.

create or replace function public.current_app_role()
returns public.app_role
language sql
stable
security definer
set search_path = public
as $$
    select role from public.users where id = auth.uid();
$$;

create or replace function public.current_department_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select department_id from public.users where id = auth.uid();
$$;

create or replace function public.current_faculty_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select id from public.faculty where user_id = auth.uid();
$$;

create or replace function public.handle_auth_user_sync()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    resolved_name text;
    resolved_role public.app_role;
    resolved_department uuid;
begin
    resolved_name := coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1));
    resolved_role := coalesce((new.raw_app_meta_data ->> 'role')::public.app_role, 'faculty'::public.app_role);
    resolved_department := nullif(new.raw_app_meta_data ->> 'department_id', '')::uuid;

    insert into public.users (id, full_name, email, role, department_id)
    values (new.id, resolved_name, new.email, resolved_role, resolved_department)
    on conflict (id) do update
        set full_name = excluded.full_name,
            email = excluded.email,
            role = excluded.role,
            department_id = excluded.department_id,
            updated_at = now();

    return new;
end;
$$;

drop trigger if exists on_auth_user_sync on auth.users;
create trigger on_auth_user_sync
after insert or update on auth.users
for each row execute procedure public.handle_auth_user_sync();

-- Backfill any already-provisioned auth users.
insert into public.users (id, full_name, email, role, department_id)
select
    auth_user.id,
    coalesce(auth_user.raw_user_meta_data ->> 'full_name', split_part(auth_user.email, '@', 1)),
    auth_user.email,
    coalesce((auth_user.raw_app_meta_data ->> 'role')::public.app_role, 'faculty'::public.app_role),
    nullif(auth_user.raw_app_meta_data ->> 'department_id', '')::uuid
from auth.users as auth_user
on conflict (id) do update
    set full_name = excluded.full_name,
        email = excluded.email,
        role = excluded.role,
        department_id = excluded.department_id,
        updated_at = now();

alter table public.users enable row level security;
alter table public.departments enable row level security;
alter table public.faculty enable row level security;
alter table public.subjects enable row level security;
alter table public.students enable row level security;
alter table public.attendance enable row level security;
alter table public.face_embeddings enable row level security;

drop policy if exists users_select_policy on public.users;
create policy users_select_policy on public.users
for select
using (
    auth.uid() = id
    or public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
);

drop policy if exists users_update_policy on public.users;
create policy users_update_policy on public.users
for update
using (
    auth.uid() = id
    or public.current_app_role() = 'admin'
)
with check (
    auth.uid() = id
    or public.current_app_role() = 'admin'
);

drop policy if exists departments_select_policy on public.departments;
create policy departments_select_policy on public.departments
for select
using (
    public.current_app_role() = 'admin'
    or id = public.current_department_id()
);

drop policy if exists departments_admin_policy on public.departments;
create policy departments_admin_policy on public.departments
for all
using (public.current_app_role() = 'admin')
with check (public.current_app_role() = 'admin');

drop policy if exists faculty_select_policy on public.faculty;
create policy faculty_select_policy on public.faculty
for select
using (
    public.current_app_role() = 'admin'
    or user_id = auth.uid()
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
);

drop policy if exists faculty_manage_policy on public.faculty;
create policy faculty_manage_policy on public.faculty
for all
using (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
)
with check (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
);

drop policy if exists subjects_select_policy on public.subjects;
create policy subjects_select_policy on public.subjects
for select
using (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
    or faculty_id = public.current_faculty_id()
);

drop policy if exists subjects_manage_policy on public.subjects;
create policy subjects_manage_policy on public.subjects
for all
using (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
)
with check (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
);

drop policy if exists students_select_policy on public.students;
create policy students_select_policy on public.students
for select
using (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
    or exists (
        select 1
        from public.subjects subject
        where subject.faculty_id = public.current_faculty_id()
          and subject.department_id = students.department_id
          and subject.semester = students.semester
          and subject.section = students.section
          and subject.is_active = true
    )
);

drop policy if exists students_insert_policy on public.students;
create policy students_insert_policy on public.students
for insert
with check (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
    or exists (
        select 1
        from public.subjects subject
        where subject.faculty_id = public.current_faculty_id()
          and subject.department_id = students.department_id
          and subject.semester = students.semester
          and subject.section = students.section
          and subject.is_active = true
    )
);

drop policy if exists students_update_policy on public.students;
create policy students_update_policy on public.students
for update
using (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
)
with check (
    public.current_app_role() = 'admin'
    or (public.current_app_role() = 'hod' and department_id = public.current_department_id())
);

drop policy if exists attendance_select_policy on public.attendance;
create policy attendance_select_policy on public.attendance
for select
using (
    public.current_app_role() = 'admin'
    or exists (
        select 1
        from public.subjects subject
        where subject.id = attendance.subject_id
          and subject.department_id = public.current_department_id()
          and public.current_app_role() = 'hod'
    )
    or attendance.faculty_id = public.current_faculty_id()
);

drop policy if exists attendance_insert_policy on public.attendance;
create policy attendance_insert_policy on public.attendance
for insert
with check (
    marked_by_user_id = auth.uid()
    and (
        public.current_app_role() = 'admin'
        or exists (
            select 1
            from public.subjects subject
            where subject.id = attendance.subject_id
              and subject.department_id = public.current_department_id()
              and public.current_app_role() = 'hod'
        )
        or attendance.faculty_id = public.current_faculty_id()
    )
);

drop policy if exists attendance_update_policy on public.attendance;
create policy attendance_update_policy on public.attendance
for update
using (
    public.current_app_role() = 'admin'
    or exists (
        select 1
        from public.subjects subject
        where subject.id = attendance.subject_id
          and subject.department_id = public.current_department_id()
          and public.current_app_role() = 'hod'
    )
)
with check (
    public.current_app_role() = 'admin'
    or exists (
        select 1
        from public.subjects subject
        where subject.id = attendance.subject_id
          and subject.department_id = public.current_department_id()
          and public.current_app_role() = 'hod'
    )
);

drop policy if exists face_embeddings_no_client_access on public.face_embeddings;
create policy face_embeddings_no_client_access on public.face_embeddings
for select
using (false);

comment on function public.handle_auth_user_sync() is 'Synchronizes auth.users into public.users using trusted app metadata. Disable open signup before relying on role metadata.';