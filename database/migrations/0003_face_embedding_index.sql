-- Phase 3 migration: HNSW index for fast ArcFace embedding search via pgvector.
--
-- The HNSW index on cosine distance is the recommended production index for
-- high-dimensional vectors with pgvector >= 0.5.  It offers sub-linear search
-- time with good recall and does not require a fixed `lists` parameter like
-- IVFFlat — making it safe to create even on an empty table.
--
-- Parameters:
--   m               = 16   (connections per layer; 16 is a good default)
--   ef_construction = 64   (build-time search width; higher = better recall)
--
-- Additionally, RLS is enabled on face_embeddings and a restrictive policy is
-- added: service-role users (backend) see everything; authenticated users see
-- only rows where the linked student belongs to their department.

-- 1. HNSW cosine-distance index
create index if not exists face_embeddings_embedding_hnsw_idx
    on public.face_embeddings
    using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

-- 2. Covering index for common lookup patterns
create index if not exists face_embeddings_student_status_idx
    on public.face_embeddings (student_id, status)
    where status = 'active';

-- 3. Enable RLS on face_embeddings (safe to run twice — IF NOT EXISTS equivalent)
alter table public.face_embeddings enable row level security;

-- 4. Service-role bypass (backend uses service key)
do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename  = 'face_embeddings'
          and policyname = 'service_role_all'
    ) then
        execute $policy$
            create policy service_role_all
                on public.face_embeddings
                for all
                to service_role
                using (true)
                with check (true)
        $policy$;
    end if;
end $$;

-- 5. Faculty / HOD can read embeddings for students in their department
do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename  = 'face_embeddings'
          and policyname = 'authenticated_read_own_dept'
    ) then
        execute $policy$
            create policy authenticated_read_own_dept
                on public.face_embeddings
                for select
                to authenticated
                using (
                    student_id in (
                        select s.id
                        from   public.students s
                        join   public.users    u on u.id = auth.uid()
                        where  s.department_id = u.department_id
                    )
                )
        $policy$;
    end if;
end $$;
