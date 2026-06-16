-- DevSelect D1 hardening: table grants.
--
-- DO NOT RUN until these table names and existing policies have been verified
-- against the current Supabase project.
--
-- Intent:
--   - checkpoint tables are backend-only.
--   - frontend must never access checkpoint tables.
--   - anon users should not have direct chats/messages DML grants.
--   - authenticated users keep the grants required by the frontend.
--   - RLS policies on chats/messages still enforce auth.uid() ownership.

-- LangGraph checkpoint tables: backend-only.
-- FastAPI uses DATABASE_URL / AsyncPostgresSaver for checkpoint operations.
-- Frontend does not need anon/authenticated access.
revoke all privileges on table public.checkpoints from anon, authenticated;
revoke all privileges on table public.checkpoint_blobs from anon, authenticated;
revoke all privileges on table public.checkpoint_writes from anon, authenticated;
revoke all privileges on table public.checkpoint_migrations from anon, authenticated;

-- User-facing chat tables: block anonymous browser DML.
revoke all privileges on table public.chats from anon;
revoke all privileges on table public.messages from anon;

-- Authenticated frontend access.
-- RLS policies must still restrict rows to the owning user.
grant select, insert, update, delete on table public.chats to authenticated;
grant select, insert, update, delete on table public.messages to authenticated;
