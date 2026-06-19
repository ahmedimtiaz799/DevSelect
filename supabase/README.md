# DevSelect Supabase Notes

This folder contains local migration and verification files for DevSelect.

The D1 migration stack has been applied to and validated on the separate
`devselect-staging` environment:

1. `000_init_devselect_staging_schema.sql`
2. `001_harden_table_grants.sql`
3. `002_add_core_indexes.sql`

Staging validation was completed before any main changes. Main `devselect` was
then inspected and backed up before hardening. Because main already contained
the application schema and data, `000_init_devselect_staging_schema.sql` was
intentionally skipped there. Migrations `001_harden_table_grants.sql` and
`002_add_core_indexes.sql` were applied successfully to main and followed by
backend and read-only frontend smoke tests.

See `supabase/MAIN_HARDENING_LOG.md` for the completed main sequence, validation
results, and remaining test boundaries.

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

The executable migration stack was validated on staging first. Main hardening
was then completed with `001` and `002`; the staging-only schema initializer
`000` was intentionally not applied to main. The comment-only baseline remains
documentation and must not be applied.

Validated on staging:

- app and checkpoint tables exist
- app and checkpoint RLS posture was verified
- table grants and core indexes were verified
- backend `/health` passed after the full migration stack
- manual RLS verification passed
- frontend Google OAuth, session refresh, and sidebar/chat-history reads passed

Validated on main:

- main schema and data were inspected before changes
- a backup/export was created before hardening
- `001_harden_table_grants.sql` was applied successfully
- backend `/health` returned 200 after `001`
- `002_add_core_indexes.sql` was applied successfully
- backend `/health` returned 200 after `002`
- manual main-account sign-in and the authenticated `/chat` route passed
- the sidebar loaded 54 existing chats
- one existing chat and its messages loaded read-only
- refresh preserved the session, sidebar, and opened-chat read path
- the D4 safe write-path test created one frontend chat row
- the D4 test persisted the user message and CV-upload guidance message
- both D4 messages and the sidebar chat persisted after refresh
- D4 used direct Supabase/PostgREST writes only; no `/api/chat`, `/upload`,
  `/stream`, `/resume`, or `/follow-up` request occurred
- no Supabase/Postgres permission, RLS, grant, or browser HTTP 4xx/5xx errors
  were observed
- no CV upload, evaluation, SSE, or AI/provider flow was triggered
- no rollback was required

Still pending:

- `/api/chat`, CV upload, `/upload`, `/stream`, and `/resume`
- evaluation, SSE streaming, and follow-up API behavior
- final report and follow-up persistence
- Gemini, Groq, LlamaParse, or GitHub provider flows

Clicking `New Chat` alone remains navigation/local state and does not create a
database row. D4 created the disposable row only after sending the approved
plain-text, no-CV test message. The first verification refreshed prematurely;
the same approved message was then retried safely in the still-empty disposable
chat. The final result was one chat with two persisted messages.

The disposable D4 `New Chat` remains in main and should be removed later only
through the normal safe UI delete path or an explicitly documented cleanup
plan.

The main frontend smoke test produced a small, non-blocking Supabase auth
device clock-skew warning. Sync Windows system time before further auth testing.

Before broader production use:

1. Sync Windows system time and repeat auth checks if the warning persists.
2. Clean up the disposable D4 chat through an approved safe path.
3. Validate `/api/chat`, upload, stream, resume, evaluation, and SSE behavior.
4. Validate final report and follow-up persistence.
5. Validate provider flows under an explicitly approved test plan.

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
