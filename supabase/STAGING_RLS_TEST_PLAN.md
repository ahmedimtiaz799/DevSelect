# DevSelect D1 Staging RLS Test Plan

This plan is for staging verification only. Do not run these steps against
production until staging has passed and the results have been reviewed.

No SQL in this folder has been applied yet.

## Preconditions

- Confirm there is a separate Supabase staging project.
- Confirm staging uses disposable data or has a current backup/export.
- Confirm staging environment variables are separate from production.
- Confirm `SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` remain backend-only.
- Confirm `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are the only
  frontend Supabase variables.
- Confirm the current local `supabase/` draft files are committed before
  staging execution.
- Confirm no real candidate CVs or private candidate data are required for RLS
  testing.
- Confirm `supabase/migrations/000_baseline_current_schema.sql` is treated as a
  documentation snapshot only, not as an executable migration.

## Apply To Staging Only

Apply only these draft migrations to staging, after review:

1. `supabase/migrations/001_harden_table_grants.sql`
2. `supabase/migrations/002_add_core_indexes.sql`

Do not apply automatically:

- `supabase/migrations/000_baseline_current_schema.sql`
- `supabase/rls_manual_tests.sql`

`rls_manual_tests.sql` should be run manually, in a controlled staging SQL
session, without service-role context.

## Staging Apply Order

1. Backup/export the current staging schema.
2. Confirm the real staging schema matches the local baseline snapshot.
3. Apply `001_harden_table_grants.sql` to staging.
4. Apply `002_add_core_indexes.sql` to staging.
5. Verify table grants for `anon`, `authenticated`, `service_role`, and
   `postgres`.
6. Verify RLS is still enabled on `chats`, `messages`, and checkpoint tables.
7. Verify `chats` and `messages` policies still exist and still enforce
   `auth.uid()` ownership.
8. Verify checkpoint tables still have no anon/authenticated user policies.
9. Run `rls_manual_tests.sql` manually using anon/authenticated context only.
10. Run a frontend login and chat-history smoke test.
11. Run a backend evaluation/checkpoint smoke test.
12. Run a follow-up persistence smoke test after a completed report.

## Manual RLS Test Checklist

- Anonymous role cannot select from `public.chats`.
- Anonymous role cannot insert into `public.chats`.
- Anonymous role cannot update `public.chats`.
- Anonymous role cannot delete from `public.chats`.
- Anonymous role cannot select from `public.messages`.
- Anonymous role cannot insert into `public.messages`.
- Anonymous role cannot update `public.messages`.
- Anonymous role cannot delete from `public.messages`.
- Authenticated User A can read their own chats.
- Authenticated User A can create their own chat.
- Authenticated User A can read messages for their own chat.
- Authenticated User A can insert messages into their own chat.
- Authenticated User B cannot read User A's chat.
- Authenticated User B cannot update User A's chat.
- Authenticated User B cannot delete User A's chat.
- Authenticated User B cannot insert a message into User A's chat.
- Authenticated users cannot read `public.checkpoints`.
- Authenticated users cannot read `public.checkpoint_blobs`.
- Authenticated users cannot read `public.checkpoint_writes`.
- Authenticated users cannot read `public.checkpoint_migrations`.
- Frontend chat history still loads after login.
- Frontend message history still loads after opening a chat.
- New user messages still persist.
- Assistant messages still persist.
- Follow-up messages still persist.
- Backend service-role chat/message operations still work.
- Backend LangGraph checkpoints still write/read through `DATABASE_URL`.
- A completed evaluation can still be resumed/read through the normal app flow.

## Rollback Plan

Do not rollback blindly. First collect:

- Supabase/PostgREST error messages.
- Browser network status codes and response bodies.
- Backend logs for chat/message failures.
- Backend logs for checkpoint read/write failures.
- The exact failing role: `anon`, `authenticated`, service-role backend, or
  direct Postgres checkpoint connection.
- The exact failing table and operation.

If frontend chat/message access breaks:

- Confirm whether RLS policy failure or table privilege failure caused it.
- If table privileges caused it, temporarily restore the minimum missing
  `authenticated` privilege on `public.chats` or `public.messages` in staging.
- Do not restore anon grants unless a reviewed product requirement proves anon
  access is needed.

If backend checkpoint access breaks:

- Confirm whether the backend is using the expected privileged `DATABASE_URL`.
- Confirm checkpoint table ownership and direct Postgres role privileges.
- Do not add anon/authenticated checkpoint policies as a rollback.
- Prefer fixing the backend database role/connection permissions in staging.

If new indexes cause unexpected issues:

- Collect the exact index name and error.
- Drop only the specific new index that caused the issue.
- Do not drop primary key or existing production indexes.

Rollback should be staging-only until the cause is understood and documented.

## Production Gate

Production remains blocked until all of these pass:

- Staging grant hardening succeeds.
- Staging index migration succeeds.
- Manual RLS tests pass.
- Frontend login and chat-history smoke test passes.
- User and assistant message persistence passes.
- Follow-up message persistence passes.
- Backend evaluation flow passes.
- Backend checkpoint write/read flow passes.
- No checkpoint access is available to frontend/browser roles.
- No secrets are exposed to frontend/Vite.
- No production data is required for testing.
- Retention cleanup is planned separately.
- Cost-control hardening is planned separately.

## Risk Ratings

| Item | Risk | Reason |
| --- | --- | --- |
| Grant hardening | Medium | Correct direction, but can break frontend if required authenticated grants are missing. |
| Index migration | Low | Adds non-destructive indexes with `if not exists`; verify columns first. |
| Manual RLS tests | Low | Safe if run in staging without service role and wrapped in rollback where appropriate. |
| Backend checkpoint smoke test | Medium | Confirms critical LangGraph behavior after grant changes; failure blocks production. |
| Production rollout | High | Should happen only after staging tests and rollback notes are complete. |

## Final Notes

- Keep checkpoint tables backend-only.
- Keep `FORCE ROW LEVEL SECURITY` deferred until service-role/backend behavior is
  verified in staging.
- Do not apply manual test SQL automatically.
- Do not run staging tests with service-role context unless the test explicitly
  targets backend/service-role behavior.
