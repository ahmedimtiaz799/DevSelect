# DevSelect D1 Staging Apply Checklist

Use this checklist only after a separate Supabase staging project or branch has
been confirmed.

Do not use production/main as staging.

## Pre-Apply Gate

Stop unless every item below is true:

- This is a separate Supabase staging project or staging branch.
- Staging is not production/main.
- Staging environment values are stored outside Git.
- `backend/.env.staging` is ignored by Git.
- `frontend/.env.staging` is ignored by Git.
- Production env files are untouched.
- Staging has a schema backup/export or disposable data.
- No real candidate CV data is needed for these tests.
- The person applying SQL knows which Supabase project is staging.
- The person applying SQL has the rollback notes ready.

## Files To Apply To Staging Only

Apply only:

1. `supabase/migrations/001_harden_table_grants.sql`
2. `supabase/migrations/002_add_core_indexes.sql`

Do not apply:

- `supabase/migrations/000_baseline_current_schema.sql`
- `supabase/rls_manual_tests.sql` automatically

`000_baseline_current_schema.sql` is documentation only.

`rls_manual_tests.sql` is manual verification SQL. Run it only in a controlled
staging SQL session and not with service-role context.

## Exact Apply Order

1. Take a staging schema backup/export.
2. Confirm current staging tables exist:
   - `public.chats`
   - `public.messages`
   - `public.checkpoints`
   - `public.checkpoint_blobs`
   - `public.checkpoint_writes`
   - `public.checkpoint_migrations`
3. Confirm current RLS policies exist for `public.chats` and `public.messages`.
4. Confirm checkpoint tables have no anon/authenticated user policies.
5. Apply `supabase/migrations/001_harden_table_grants.sql` to staging.
6. Verify grants after `001`.
7. Apply `supabase/migrations/002_add_core_indexes.sql` to staging.
8. Verify indexes after `002`.
9. Run manual RLS tests using anon/authenticated context only.
10. Run frontend staging smoke tests.
11. Run backend staging evaluation/checkpoint smoke tests.
12. Document results before any production discussion.

## Post-001 Verification Checklist

After applying `001_harden_table_grants.sql`, verify:

- anon cannot select `public.chats`.
- anon cannot insert into `public.chats`.
- anon cannot update `public.chats`.
- anon cannot delete from `public.chats`.
- anon cannot select `public.messages`.
- anon cannot insert into `public.messages`.
- anon cannot update `public.messages`.
- anon cannot delete from `public.messages`.
- authenticated users can access their own chats.
- authenticated users can access messages for their own chats.
- authenticated users cannot access another user's chats.
- authenticated users cannot access another user's messages.
- authenticated users cannot insert messages into another user's chat.
- authenticated users cannot read `public.checkpoints`.
- authenticated users cannot read `public.checkpoint_blobs`.
- authenticated users cannot read `public.checkpoint_writes`.
- authenticated users cannot read `public.checkpoint_migrations`.
- checkpoint tables still have no anon/authenticated user policies.
- backend service/database path can still access checkpoint tables.

## Post-002 Verification Checklist

After applying `002_add_core_indexes.sql`, verify:

- `idx_chats_user_id` exists.
- `idx_chats_user_id_updated_at_desc` exists.
- `idx_messages_chat_id_created_at` exists.
- old `idx_messages_chat_id` still exists unless intentionally removed later.
- no table data changed.
- chat history queries still perform normally.
- message loading still performs normally.

## Frontend Staging Smoke Test

Use staging frontend and staging backend only.

- Login works.
- New chat creation works.
- Chat history loads.
- User message persistence works.
- Assistant message persistence works.
- Follow-up message persistence works.
- Logout then login still shows the correct user's data.
- User B cannot see User A chats.
- User B cannot open User A chat URL directly.
- User B cannot see User A messages.

## Backend Staging Smoke Test

Use staging backend env only.

- Backend boots with staging env.
- Service role key remains backend-only.
- Database connection for LangGraph checkpoints remains backend-only.
- LangGraph checkpoint write/read works.
- One controlled CV evaluation completes.
- SSE stream still emits status/token/done or controlled error events.
- Final report persists to `public.messages`.
- Follow-up after completed report works.
- Follow-up messages persist to `public.messages`.
- No checkpoint permission errors appear in backend logs.
- No frontend/browser role can read checkpoint tables.

## Rollback Plan

Do not rollback blindly. First collect:

- Supabase/PostgREST errors.
- Browser Network tab status codes and response bodies.
- Backend logs for chat/message failures.
- Backend logs for checkpoint failures.
- Which role failed: anon, authenticated, service-role backend, or direct
  database checkpoint connection.
- Which table failed.
- Which operation failed.

If frontend chat/message access breaks:

- Confirm whether the failure is a grant problem or RLS policy problem.
- Restore only the minimum missing authenticated grant in staging.
- Do not restore anon grants unless a reviewed product requirement proves anon
  access is needed.

If backend checkpoint access breaks:

- Confirm the backend is using the expected staging database connection.
- Confirm checkpoint table owner and role privileges.
- Do not add anon/authenticated checkpoint policies as rollback.
- Prefer fixing backend database role permissions.

If a new index causes trouble:

- Identify the exact new index name.
- Drop only the specific new index in staging.
- Do not drop primary keys or pre-existing indexes.

Never run rollback steps on production by mistake.

## Production Gate

Production remains blocked until:

- Staging grant hardening passes.
- Staging indexes pass.
- Manual RLS tests pass.
- Frontend smoke tests pass.
- Backend checkpoint/evaluation smoke tests pass.
- No secrets are exposed.
- Retention cleanup work is tracked separately.
- Cost-control hardening work is tracked separately.
- Rollback notes are documented.

## Risk Labels

| Item | Risk | Why |
| --- | --- | --- |
| Applying `001_harden_table_grants.sql` | Medium | Correctly tightens access, but can break frontend if required authenticated grants are missing. |
| Applying `002_add_core_indexes.sql` | Low | Adds non-destructive indexes with `if not exists`; still verify column names first. |
| Manual RLS testing | Low | Safe in staging if not run with service role and if writes are wrapped or disposable. |
| Frontend smoke testing | Low | Uses normal staging app behavior and should not require real candidate data. |
| Backend checkpoint testing | Medium | Critical path for LangGraph; failures block production rollout. |
| Production rollout | High | Only safe after staging, rollback notes, retention, and cost-control planning. |

## Final Decision

- If every staging check passes, document results and plan production review.
- If any staging check fails, stop and fix staging first.
- If staging identity is uncertain, stop.
- If only production exists, stop.
