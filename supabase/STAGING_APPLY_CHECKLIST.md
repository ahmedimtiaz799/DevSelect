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

1. `supabase/migrations/000_init_devselect_staging_schema.sql`
2. `supabase/migrations/001_harden_table_grants.sql`
3. `supabase/migrations/002_add_core_indexes.sql`

Do not apply:

- `supabase/migrations/000_baseline_current_schema.sql`
- `supabase/rls_manual_tests.sql` automatically

`000_baseline_current_schema.sql` is documentation only.

`000_init_devselect_staging_schema.sql` is a staging-only schema init draft.
Review it before applying, and do not apply it to production without separate
review.

`rls_manual_tests.sql` is manual verification SQL. Run it only in a controlled
staging SQL session and not with service-role context.

## Exact Apply Order

1. Take a staging schema backup/export.
2. If staging is empty/new, apply
   `supabase/migrations/000_init_devselect_staging_schema.sql` to staging.
3. Run normal staging backend startup once to allow the LangGraph Postgres
   checkpointer to create/check its checkpoint tables.
4. Confirm current staging tables exist:
   - `public.chats`
   - `public.messages`
   - `public.checkpoints`
   - `public.checkpoint_blobs`
   - `public.checkpoint_writes`
   - `public.checkpoint_migrations`
5. Confirm current RLS policies exist for `public.chats` and `public.messages`.
6. Confirm checkpoint tables have no anon/authenticated user policies.
7. Apply `supabase/migrations/001_harden_table_grants.sql` to staging.
8. Verify grants and checkpoint RLS after `001`.
9. Run a normal-lifespan backend `/health` smoke test after `001`.
10. Apply `supabase/migrations/002_add_core_indexes.sql` to staging.
11. Verify indexes after `002`.
12. Run a normal-lifespan backend `/health` smoke test after `002`.
13. Run manual RLS tests using anon/authenticated context only.
14. Run the frontend staging OAuth/session/sidebar smoke test.
15. Document validated and pending results before any production discussion.

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
- RLS is enabled on `public.checkpoints`.
- RLS is enabled on `public.checkpoint_blobs`.
- RLS is enabled on `public.checkpoint_writes`.
- RLS is enabled on `public.checkpoint_migrations`.
- checkpoint tables still have no anon/authenticated user policies.
- authenticated has only `SELECT`, `INSERT`, `UPDATE`, `DELETE` on
  `public.chats`.
- authenticated has only `SELECT`, `INSERT`, `UPDATE`, `DELETE` on
  `public.messages`.
- authenticated does not have `TRUNCATE`, `REFERENCES`, or `TRIGGER` on
  `public.chats`.
- authenticated does not have `TRUNCATE`, `REFERENCES`, or `TRIGGER` on
  `public.messages`.
- backend service/database path can still access checkpoint tables.
- backend still boots after grant hardening.

## Post-002 Verification Checklist

After applying `002_add_core_indexes.sql`, verify:

- `idx_chats_user_id` exists.
- `idx_chats_user_id_updated_at_desc` exists.
- `idx_messages_chat_id_created_at` exists.
- old `idx_messages_chat_id` still exists unless intentionally removed later.
- no table data changed.
- chat history queries still perform normally.
- message loading still performs normally.

## Validated Staging Results

The following checks passed on the separate staging environment:

- `000_init_devselect_staging_schema.sql` applied successfully.
- Normal backend startup created/checked the LangGraph checkpoint tables.
- `001_harden_table_grants.sql` applied successfully.
- Normal-lifespan backend `/health` passed after `001`.
- `002_add_core_indexes.sql` applied successfully.
- Normal-lifespan backend `/health` passed after `002`.
- Manual RLS verification passed using disposable staging users.
- Frontend Google OAuth login returned to authenticated `/chat`.
- The authenticated session persisted after refresh.
- Sidebar/chat-history reads completed without visible RLS or auth errors.
- Staging Supabase was used; main/production Supabase was not contacted.
- No `/api/chat`, `/upload`, `/stream`, evaluation, or provider call occurred
  during the frontend smoke test.

`New Chat` was observed to be navigation/local state only and did not create a
database row during the safe frontend smoke test.

## Pending / Not Validated

The following behavior remains explicitly untested:

- frontend-created `public.chats` row persistence
- frontend-created `public.messages` row persistence
- `/api/chat`
- CV upload and `/upload`
- `/stream`
- evaluation pipeline
- SSE streaming
- final report persistence
- follow-up persistence
- Gemini, Groq, LlamaParse, and GitHub provider flows

These checks require a separate approved staging test. Do not infer that they
passed from the OAuth/session/sidebar smoke test.

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
- Frontend OAuth/session/sidebar smoke tests pass.
- Frontend chat/message write persistence passes.
- Backend evaluation/checkpoint flows pass.
- Final report and follow-up persistence pass.
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
