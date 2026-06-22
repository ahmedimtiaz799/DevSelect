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

-- ---------------------------------------------------------------------------
-- 8. authenticated User A can create a chat with allowed frontend columns.
-- Expected: insert succeeds and is rolled back.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
insert into public.chats (user_id, title)
values ('USER_A_UUID', 'Gate 2 allowed chat insert test')
returning id;
rollback;

-- ---------------------------------------------------------------------------
-- 9. RLS WITH CHECK blocks User A from creating a chat for User B.
-- Expected: insert is rejected by the existing chats ownership policy.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
insert into public.chats (user_id, title)
values ('USER_B_UUID', 'Gate 2 forbidden cross-user chat insert');
rollback;

-- ---------------------------------------------------------------------------
-- 10. authenticated User A cannot create or update backend-owned thread_id.
-- Expected: both statements fail with a column permission denial.
-- Each denial is isolated because it aborts its transaction.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
insert into public.chats (user_id, title, thread_id)
values (
  'USER_A_UUID',
  'Gate 2 forbidden thread insert test',
  'gate2-forbidden-client-thread'
);
rollback;

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
update public.chats
set thread_id = 'gate2-forbidden-client-thread'
where id = 'USER_A_CHAT_ID';
rollback;

-- ---------------------------------------------------------------------------
-- 11. authenticated User A can rename and pin their own existing chat.
-- Expected: the update affects USER_A_CHAT_ID and is rolled back.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
update public.chats
set
  title = 'Gate 2 allowed rename test',
  updated_at = now(),
  is_pinned = true,
  pinned_at = now()
where id = 'USER_A_CHAT_ID'
returning id, title, is_pinned;
rollback;

-- ---------------------------------------------------------------------------
-- 12. authenticated User A can insert a message into their own chat.
-- Expected: insert succeeds and is rolled back.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
insert into public.messages (chat_id, role, content)
values (
  'USER_A_CHAT_ID',
  'user',
  'Gate 2 allowed own-message insert test'
)
returning id;
rollback;

-- ---------------------------------------------------------------------------
-- 13. authenticated users cannot update or directly delete messages.
-- Expected: both statements fail with a table/column permission denial.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
update public.messages
set content = 'Gate 2 forbidden message update'
where chat_id = 'USER_A_CHAT_ID';
rollback;

begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_A_UUID', true);
delete from public.messages
where chat_id = 'USER_A_CHAT_ID';
rollback;

-- ---------------------------------------------------------------------------
-- 14. authenticated User B cannot update/delete User A chat or read messages.
-- Expected: updates/deletes affect zero rows and message select returns zero.
-- ---------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'USER_B_UUID', true);
update public.chats
set title = 'Gate 2 forbidden cross-user rename'
where id = 'USER_A_CHAT_ID'
returning id;
delete from public.chats
where id = 'USER_A_CHAT_ID'
returning id;
select * from public.messages
where chat_id = 'USER_A_CHAT_ID';
rollback;

-- ---------------------------------------------------------------------------
-- 15. duplicate non-null thread_id values are rejected.
-- Run this constraint check in the privileged staging SQL session, not while
-- set to anon/authenticated. Both disposable rows are inside this rollback.
-- Expected: the second insert fails with a unique-constraint violation.
-- ---------------------------------------------------------------------------
begin;
insert into public.chats (user_id, title, thread_id)
values (
  'USER_A_UUID',
  'Gate 2 unique thread test A',
  'gate2-duplicate-thread-test'
);
insert into public.chats (user_id, title, thread_id)
values (
  'USER_A_UUID',
  'Gate 2 unique thread test B',
  'gate2-duplicate-thread-test'
);
rollback;
