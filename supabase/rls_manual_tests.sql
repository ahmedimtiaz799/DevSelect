-- DevSelect manual RLS checks.
--
-- STAGING ONLY.
-- DO NOT RUN WITH SERVICE ROLE AS THE TEST CONTEXT.
-- DO NOT RUN AGAINST PRODUCTION UNTIL REVIEWED.
-- USE DISPOSABLE STAGING USERS ONLY.
-- ALL TEST DATA MUST BE INSIDE TRANSACTIONS WITH ROLLBACK.
--
-- These snippets are for manual verification in a controlled staging SQL
-- session. They should not be run automatically by a migration tool.
--
-- Notes:
--   - Replace USER_A_UUID, USER_B_UUID, and USER_A_CHAT_ID before use.
--   - USER_A_CHAT_ID must be an existing staging chat owned by USER_A_UUID.
--   - Zero rows are only meaningful when the referenced test row exists.
--   - auth.uid() depends on request.jwt.claim.sub.
--   - set local role anon/authenticated simulates frontend API roles.
--   - If your SQL environment runs as table owner or another privileged role,
--     results may not reflect normal PostgREST/Supabase client behavior.
--   - Each expected-denial statement is isolated in its own transaction because
--     permission/RLS errors abort the current transaction until rollback.
--
-- Placeholder values to replace before running:
--   USER_A_UUID
--   USER_B_UUID
--   USER_A_CHAT_ID

-- ---------------------------------------------------------------------------
-- 1. anon cannot select from chats/messages.
-- Expected: permission/RLS denial, or zero rows if the SQL environment masks
-- denied rows. A zero-row result is only meaningful if staging has rows.
-- ---------------------------------------------------------------------------
begin;
set local role anon;
select * from public.chats limit 1;
rollback;

begin;
set local role anon;
select * from public.messages limit 1;
rollback;

-- ---------------------------------------------------------------------------
-- 2. anon cannot insert into chats/messages.
-- Expected: permission/RLS denial. Both attempts are rolled back.
-- ---------------------------------------------------------------------------
begin;
set local role anon;
insert into public.chats (user_id, title)
values ('USER_A_UUID', 'RLS anon insert test - should not persist');
rollback;

begin;
set local role anon;
insert into public.messages (chat_id, role, content)
values (
  'USER_A_CHAT_ID',
  'user',
  'RLS anon message insert test - should not persist'
);
rollback;

-- ---------------------------------------------------------------------------
-- 3. anon cannot access checkpoint tables.
-- Expected: permission/RLS denial or zero rows.
-- ---------------------------------------------------------------------------
begin;
set local role anon;
select * from public.checkpoints limit 1;
rollback;

begin;
set local role anon;
select * from public.checkpoint_blobs limit 1;
rollback;

begin;
set local role anon;
select * from public.checkpoint_writes limit 1;
rollback;

begin;
set local role anon;
select * from public.checkpoint_migrations limit 1;
rollback;

-- ---------------------------------------------------------------------------
-- 4. authenticated User A can access own chats/messages.
-- Expected: USER_A_CHAT_ID is visible. Message query returns own messages for
-- that chat. Zero rows are inconclusive unless USER_A_CHAT_ID exists and has
-- messages.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
select * from public.chats
where id = 'USER_A_CHAT_ID';
select m.*
from public.messages m
where m.chat_id = 'USER_A_CHAT_ID'
limit 10;
rollback;

-- ---------------------------------------------------------------------------
-- 5. authenticated User B cannot read User A chat.
-- Expected: zero rows. This is only meaningful if USER_A_CHAT_ID exists and is
-- owned by USER_A_UUID.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_B_UUID', true);
select * from public.chats
where id = 'USER_A_CHAT_ID';
rollback;

-- ---------------------------------------------------------------------------
-- 6. authenticated User B cannot insert into User A chat.
-- Expected: insert blocked by RLS/ownership policy. Attempt is rolled back.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_B_UUID', true);
insert into public.messages (chat_id, role, content)
values (
  'USER_A_CHAT_ID',
  'user',
  'RLS User B ownership test - should not insert into User A chat'
);
rollback;

-- ---------------------------------------------------------------------------
-- 7. authenticated users cannot access checkpoint tables.
-- Expected: permission/RLS denial or zero rows.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
select * from public.checkpoints limit 1;
rollback;

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
select * from public.checkpoint_blobs limit 1;
rollback;

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
select * from public.checkpoint_writes limit 1;
rollback;

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
select * from public.checkpoint_migrations limit 1;
rollback;
