-- Canonical Phase 1 schema for Supabase PostgreSQL + pgvector.
-- This file defines the production data model that Phase 2 will implement through migrations.

create extension if not exists vector;
create extension if not exists pgcrypto;

do $$
begin
    create type public.app_role as enum ('admin', 'hod', 'faculty');
exception
    when duplicate_object then null;
end $$;

do $$
begin
    create type public.attendance_status as enum ('present', 'late', 'absent', 'excused');
exception
    when duplicate_object then null;
end $$;

do $$
begin
    create type public.face_sample_source as enum ('camera', 'upload', 'imported');
exception
    when duplicate_object then null;
end $$;

do $$
begin
    create type public.face_embedding_status as enum ('active', 'deprecated', 'rejected');
exception
    when duplicate_object then null;
end $$;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create table if not exists public.departments (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,
    name text not null unique,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.users (
    id uuid primary key references auth.users (id) on delete cascade,
    full_name text not null,
    email text not null unique,
    role public.app_role not null,
    department_id uuid references public.departments (id) on delete set null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.departments
    add column if not exists hod_user_id uuid unique references public.users (id) on delete set null;

create table if not exists public.faculty (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references public.users (id) on delete cascade,
    department_id uuid not null references public.departments (id) on delete restrict,
    employee_code text not null unique,
    designation text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.subjects (
    id uuid primary key default gen_random_uuid(),
    code text not null,
    name text not null,
    department_id uuid not null references public.departments (id) on delete restrict,
    faculty_id uuid not null references public.faculty (id) on delete restrict,
    semester smallint not null check (semester between 1 and 12),
    section text not null,
    attendance_grace_minutes integer not null default 15 check (attendance_grace_minutes between 0 and 180),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (department_id, code, semester, section)
);

create table if not exists public.students (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    roll_number text not null,
    department_id uuid not null references public.departments (id) on delete restrict,
    semester smallint not null check (semester between 1 and 12),
    section text not null,
    batch_year integer not null check (batch_year between 2000 and 2100),
    email text,
    image_url text,
    status text not null default 'active',
    created_by uuid references public.users (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (department_id, roll_number),
    unique (email)
);

create table if not exists public.face_embeddings (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students (id) on delete cascade,
    embedding vector(512) not null,
    model_name text not null default 'arcface',
    model_version text not null,
    sample_source public.face_sample_source not null,
    storage_path text,
    quality_score numeric(5,4) not null check (quality_score >= 0 and quality_score <= 1),
    landmarks jsonb not null default '{}'::jsonb,
    is_primary boolean not null default false,
    status public.face_embedding_status not null default 'active',
    created_by uuid references public.users (id) on delete set null,
    created_at timestamptz not null default now()
);

create table if not exists public.attendance (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students (id) on delete restrict,
    subject_id uuid not null references public.subjects (id) on delete restrict,
    faculty_id uuid not null references public.faculty (id) on delete restrict,
    marked_by_user_id uuid not null references public.users (id) on delete restrict,
    class_date date not null,
    session_key text not null,
    session_label text not null,
    status public.attendance_status not null default 'present',
    confidence_score numeric(5,4) not null check (confidence_score >= 0 and confidence_score <= 1),
    captured_at timestamptz not null default now(),
    recognition_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (student_id, subject_id, class_date, session_key)
);

create index if not exists idx_users_department_role
    on public.users (department_id, role);

create index if not exists idx_faculty_department
    on public.faculty (department_id);

create index if not exists idx_subjects_faculty_active
    on public.subjects (faculty_id, is_active);

create index if not exists idx_students_department_semester_section
    on public.students (department_id, semester, section);

create index if not exists idx_attendance_subject_date
    on public.attendance (subject_id, class_date);

create index if not exists idx_attendance_student_date
    on public.attendance (student_id, class_date);

create index if not exists idx_attendance_faculty_date
    on public.attendance (faculty_id, class_date);

create index if not exists idx_face_embeddings_student_status
    on public.face_embeddings (student_id, status);

create unique index if not exists uniq_primary_embedding_per_student
    on public.face_embeddings (student_id)
    where is_primary and status = 'active';

create index if not exists idx_face_embeddings_vector
    on public.face_embeddings
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

drop trigger if exists set_departments_updated_at on public.departments;
create trigger set_departments_updated_at
before update on public.departments
for each row execute function public.set_updated_at();

drop trigger if exists set_users_updated_at on public.users;
create trigger set_users_updated_at
before update on public.users
for each row execute function public.set_updated_at();

drop trigger if exists set_faculty_updated_at on public.faculty;
create trigger set_faculty_updated_at
before update on public.faculty
for each row execute function public.set_updated_at();

drop trigger if exists set_subjects_updated_at on public.subjects;
create trigger set_subjects_updated_at
before update on public.subjects
for each row execute function public.set_updated_at();

drop trigger if exists set_students_updated_at on public.students;
create trigger set_students_updated_at
before update on public.students
for each row execute function public.set_updated_at();

drop trigger if exists set_attendance_updated_at on public.attendance;
create trigger set_attendance_updated_at
before update on public.attendance
for each row execute function public.set_updated_at();

-- Phase 2 note:
-- Enable Row Level Security and add policies after migrations are applied.
-- Keep vector search behind FastAPI even after pgvector is enabled.