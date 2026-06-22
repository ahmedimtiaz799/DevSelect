-- DevSelect Gate 2 hardening: authenticated write columns and safe defaults.
--
-- REVIEW BEFORE APPLYING.
-- APPLY TO STAGING FIRST.
-- PRODUCTION REQUIRES A SEPARATE BACKUP, REVIEW, AND VALIDATION SESSION.
--
-- This migration intentionally does not change:
--   - existing RLS policies
--   - service_role or postgres table privileges
--   - LangGraph checkpoint tables
--   - managed Supabase Storage objects or privileges

-- Authenticated users still need to read and delete their own chats through
-- the existing RLS ownership policy. Replace table-wide INSERT/UPDATE with
-- only the columns used by the frontend.
revoke insert, update on table public.chats from authenticated;
grant insert (user_id, title) on table public.chats to authenticated;
grant update (title, updated_at, is_pinned, pinned_at)
on table public.chats to authenticated;

-- The frontend reads and inserts messages. It does not update or directly
-- delete message rows; chat deletion removes messages through the existing
-- foreign-key cascade.
revoke insert, update, delete on table public.messages from authenticated;
grant insert (chat_id, role, content)
on table public.messages to authenticated;

-- Prevent one LangGraph checkpoint thread from being bound to multiple chats.
-- Main and staging were checked before drafting this migration and had no
-- duplicate non-null thread_id values.
create unique index if not exists idx_chats_thread_id_unique_nonnull
on public.chats (thread_id)
where thread_id is not null;

-- Future DevSelect app objects created by the postgres migration owner should
-- start private. Grant browser access explicitly in the migration that creates
-- each object after its RLS policy has been reviewed.
--
-- Supabase-managed objects created by other owners, including storage schemas,
-- are intentionally outside this migration.
alter default privileges for role postgres in schema public
revoke all privileges on tables from public, anon, authenticated;

alter default privileges for role postgres in schema public
revoke all privileges on sequences from public, anon, authenticated;

alter default privileges for role postgres in schema public
revoke execute on functions from public, anon, authenticated;
