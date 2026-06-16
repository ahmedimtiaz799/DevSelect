-- DevSelect manual RLS checks.
--
-- DO NOT RUN WITH SERVICE ROLE.
-- DO NOT RUN AGAINST PRODUCTION UNTIL REVIEWED.
--
-- These are manual verification snippets for a staging database or a carefully
-- controlled SQL session. Replace placeholder UUIDs before use.
--
-- Notes:
--   - auth.uid() depends on request.jwt.claim.sub.
--   - set role anon/authenticated is used to simulate frontend API roles.
--   - If your SQL environment runs as a table owner or privileged role, results
--     may not reflect normal PostgREST/Supabase client behavior.

-- ---------------------------------------------------------------------------
-- Placeholders
-- ---------------------------------------------------------------------------
-- User A id: 00000000-0000-0000-0000-000000000001
-- User B id: 00000000-0000-0000-0000-000000000002
-- User A chat id: 11111111-1111-1111-1111-111111111111

-- ---------------------------------------------------------------------------
-- 1. anon cannot access chats/messages
-- Expected: zero rows or permission/RLS denial.
-- ---------------------------------------------------------------------------
begin;
set local role anon;
select * from public.chats limit 1;
select * from public.messages limit 1;
rollback;

-- ---------------------------------------------------------------------------
-- 2. authenticated User B cannot read User A chat
-- Expected: zero rows.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000002', true);
select * from public.chats
where id = '11111111-1111-1111-1111-111111111111';
rollback;

-- ---------------------------------------------------------------------------
-- 3. authenticated User B cannot insert into User A chat
-- Expected: insert blocked by RLS or foreign/ownership policy.
-- Adjust columns to match the real messages schema before using.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000002', true);
insert into public.messages (chat_id, role, content)
values (
  '11111111-1111-1111-1111-111111111111',
  'user',
  'RLS ownership test - should not insert into another user chat'
);
rollback;

-- ---------------------------------------------------------------------------
-- 4. authenticated user cannot read checkpoint tables
-- Expected: permission/RLS denial or zero rows.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);
select * from public.checkpoints limit 1;
select * from public.checkpoint_blobs limit 1;
select * from public.checkpoint_writes limit 1;
select * from public.checkpoint_migrations limit 1;
rollback;

-- ---------------------------------------------------------------------------
-- 5. authenticated User A can access own chats/messages
-- Expected: own chat row is visible. Message query should return own messages.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);
select * from public.chats
where id = '11111111-1111-1111-1111-111111111111';
select m.*
from public.messages m
where m.chat_id = '11111111-1111-1111-1111-111111111111'
limit 10;
rollback;
