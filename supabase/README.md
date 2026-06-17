# DevSelect Supabase Notes

This folder contains local migration and verification drafts for DevSelect.
These files have not been applied to Supabase.

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

The migration files in `supabase/migrations/` are local drafts and are not
applied yet.

Before deployment:

1. Review the baseline snapshot against the current Supabase project.
2. Verify all table and column names used by follow-up migrations.
3. Review existing RLS policies for `chats` and `messages`.
4. Apply migrations only in staging first.
5. Run the manual RLS checks in `rls_manual_tests.sql`.
6. Confirm the FastAPI evaluation flow still works with checkpoints.

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
