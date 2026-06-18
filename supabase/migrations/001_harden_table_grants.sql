-- DevSelect D1 hardening: table grants.
--
-- DO NOT RUN until these table names and existing policies have been verified
-- against the current Supabase project.
--
-- Intent:
--   - checkpoint tables are backend-only.
--   - frontend must never access checkpoint tables.
--   - anon users should not have direct chats/messages DML grants.
--   - authenticated users keep only the grants required by the frontend.
--   - RLS policies on chats/messages still enforce auth.uid() ownership.
--   - Do not revoke from service_role or postgres.
--
-- Staging note:
--   LangGraph checkpoint access uses the backend DATABASE_URL / privileged
--   database path. Browser roles must not access checkpoint tables directly.

-- LangGraph checkpoint tables: backend-only.
-- Enable RLS and create no anon/authenticated policies. With RLS enabled and
-- no user-facing policies, browser roles remain locked out even if future
-- grants are accidentally broadened.
alter table public.checkpoints enable row level security;
alter table public.checkpoint_blobs enable row level security;
alter table public.checkpoint_writes enable row level security;
alter table public.checkpoint_migrations enable row level security;

revoke all privileges on table public.checkpoints from public;
revoke all privileges on table public.checkpoint_blobs from public;
revoke all privileges on table public.checkpoint_writes from public;
revoke all privileges on table public.checkpoint_migrations from public;
revoke all privileges on table public.checkpoints from anon, authenticated;
revoke all privileges on table public.checkpoint_blobs from anon, authenticated;
revoke all privileges on table public.checkpoint_writes from anon, authenticated;
revoke all privileges on table public.checkpoint_migrations from anon, authenticated;

-- User-facing chat tables: block anonymous browser DML.
-- Revoke broad grants first, then add back only the authenticated frontend
-- privileges required by the app. Existing RLS policies remain unchanged.
revoke all privileges on table public.chats from public;
revoke all privileges on table public.messages from public;
revoke all privileges on table public.chats from anon;
revoke all privileges on table public.messages from anon;
revoke all privileges on table public.chats from authenticated;
revoke all privileges on table public.messages from authenticated;
grant select, insert, update, delete on table public.chats to authenticated;
grant select, insert, update, delete on table public.messages to authenticated;
