# DevSelect Supabase Notes

This folder contains local migration and verification files for DevSelect.

The D1 migration stack has been applied to and validated on the separate
`devselect-staging` environment:

1. `000_init_devselect_staging_schema.sql`
2. `001_harden_table_grants.sql`
3. `002_add_core_indexes.sql`

The migration stack has not been promoted or applied to main/production.
Main/production requires a separate pre-flight review, schema backup/export,
controlled apply session, and post-apply validation.

## Architecture

- `chats` and `messages` are user-facing tables.
- The frontend uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- The frontend must never access LangGraph checkpoint tables.
- FastAPI uses `SUPABASE_SERVICE_ROLE_KEY` for backend Supabase table operations.
- LangGraph checkpoints use `DATABASE_URL` through `AsyncPostgresSaver`.

## Checkpoint Tables

Checkpoint tables are backend-only:

- `public.checkpoints`
- `public.checkpoint_blobs`
- `public.checkpoint_writes`
- `public.checkpoint_migrations`

They should keep RLS enabled with no anon/authenticated user policies. Browser
roles should not have grants on these tables.

This is safe only if `DATABASE_URL` uses a backend-only privileged Postgres
connection with the permissions LangGraph needs.

## Secrets

Never expose these to frontend/Vite:

- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`
- any direct Postgres URL

Only `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` belong in frontend env.

## Baseline Status

`supabase/migrations/000_baseline_current_schema.sql` is a snapshot document
generated from the current Supabase state during a read-only audit. It is not an
executable migration and should not be run directly.

Before using the baseline to create or repair an environment, review it against
the current Supabase project and convert it into intentional, executable
migrations.

## Migration Status

The executable migration stack has been validated on staging only. The
comment-only baseline remains documentation and must not be applied.

Validated on staging:

- app and checkpoint tables exist
- app and checkpoint RLS posture was verified
- table grants and core indexes were verified
- backend `/health` passed after the full migration stack
- manual RLS verification passed
- frontend Google OAuth, session refresh, and sidebar/chat-history reads passed

Not yet validated:

- frontend-created chat-row persistence
- frontend-created message-row persistence
- `/api/chat`, CV upload, `/upload`, and `/stream`
- evaluation and SSE streaming
- final report and follow-up persistence
- Gemini, Groq, LlamaParse, or GitHub provider flows

During the safe frontend smoke test, `New Chat` was navigation/local state only
and did not create a database row.

Before deployment:

1. Review the baseline snapshot against the target main/production project.
2. Export or back up the target schema before applying anything.
3. Verify all table, column, policy, grant, and index assumptions.
4. Run a separately approved main/production apply session.
5. Repeat post-apply backend, RLS, and frontend validation.
6. Validate the pending chat-write and evaluation flows before public use.

## FORCE RLS

`FORCE ROW LEVEL SECURITY` for `chats` and `messages` is deferred.

Reason: the backend uses service-role Supabase operations for some chat/message
paths. Force RLS should only be enabled after confirming service-role/backend
behavior and policies in staging.

## Retention Cleanup

Retention cleanup is future work. `messages` can contain sensitive CV/report
content, and LangGraph checkpoints can contain extracted CV/evaluation state.

Before public deployment, define retention rules for:

- chat messages
- generated reports
- checkpoint state
- temporary or derived CV content
