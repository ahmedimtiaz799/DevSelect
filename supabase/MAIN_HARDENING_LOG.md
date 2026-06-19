# DevSelect Main Supabase D1 Hardening Log

## Status

The D1 grant and index hardening sequence has been applied to and validated on
main `devselect`. Staging validation was completed first. No production rollback
was required.

## Preconditions

- Main was inspected before changes.
- Main already contained the application schema and existing data.
- A main backup/export was created before hardening.
- `000_init_devselect_staging_schema.sql` was intentionally skipped because it
  initializes an empty environment and was not appropriate for main.

## Applied Sequence

1. Applied `001_harden_table_grants.sql` to main.
2. Started the backend normally and confirmed `/health` returned 200.
3. Confirmed no Supabase/Postgres permission, RLS, grant, or LangGraph
   checkpoint startup errors after `001`.
4. Applied `002_add_core_indexes.sql` to main.
5. Started the backend normally and confirmed `/health` returned 200.
6. Confirmed no Supabase/Postgres permission, RLS, grant, index, or LangGraph
   checkpoint startup errors after `002`.
7. Ran the read-only frontend smoke test described below.

## Read-Only Frontend Validation

- Manual sign-in with the main account succeeded.
- The authenticated `/chat` route loaded.
- The sidebar loaded 54 existing chats.
- One existing chat opened read-only and its messages displayed.
- Refresh preserved the authenticated session, sidebar, and opened-chat read
  path.
- No Supabase/Postgres permission, RLS, or grant errors were observed.
- No browser resource returned an HTTP 4xx or 5xx response.
- No `/api/chat`, `/upload`, `/stream`, or `/resume` request was made.
- No CV upload, evaluation, SSE, or AI/provider flow was triggered.
- Git remained clean after testing.

## Pending Validation

The hardening smoke tests intentionally did not validate:

- frontend-created `public.chats` row persistence
- frontend-created `public.messages` row persistence
- `/api/chat`
- CV upload and `/upload`
- `/stream` and `/resume`
- the evaluation pipeline and SSE streaming
- final report and follow-up persistence
- Gemini, Groq, LlamaParse, or GitHub provider flows

These flows require a separate, explicitly approved write/evaluation test plan.

## Non-Blocking Warning

A small Supabase auth device clock-skew warning appeared during the frontend
test. It did not block sign-in, reads, or session persistence. Sync Windows
system time before further authentication testing.

## Rollback

No rollback was needed.
