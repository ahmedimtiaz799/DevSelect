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

## D4 Safe Write-Path Validation

- Manual authentication succeeded.
- A fresh empty `/chat` was used with no CV or other file attached.
- The approved message was `D4 safe write test - no CV - no provider call`.
- The frontend created one `public.chats` row.
- The frontend persisted two `public.messages` rows: the user message and the
  assistant CV-upload guidance message.
- The sidebar increased from 54 to 55 chats.
- Both messages and the sidebar entry persisted after refresh.
- Confirmed PostgREST writes returned:
  - `POST /rest/v1/chats`: 201
  - `PATCH /rest/v1/chats`: 200
  - `POST /rest/v1/messages`: 201
- No `/api/chat`, `/upload`, `/stream`, `/resume`, or `/follow-up` request
  occurred.
- No CV upload, evaluation, SSE, LangGraph evaluation, or AI/provider flow was
  triggered.
- No Supabase/Postgres permission, RLS, or grant error occurred.
- Git remained clean after testing.

The first verification refreshed prematurely, interrupting message persistence.
The same approved message was retried safely in the existing empty disposable
chat after confirming that no file, completed report, or follow-up state was
present. The final result was one disposable chat with two persisted messages.

## D5 Safe Cleanup/Delete Validation

- The disposable D4 chat was found by its exact approved test message.
- The normal chat context menu and delete confirmation modal were used.
- The confirmation correctly targeted the disposable `New Chat`.
- `DELETE /rest/v1/chats` returned 204.
- Existing cascade delete behavior removed the two associated messages.
- The sidebar decreased from 55 to 54 chats.
- Refresh confirmed that the deleted chat did not return.
- No `/api/chat`, `/upload`, `/stream`, `/resume`, or `/follow-up` request
  occurred.
- No CV upload, evaluation, SSE, LangGraph evaluation, or AI/provider flow was
  triggered.
- No Supabase/Postgres permission, RLS, or grant error occurred.
- Git remained clean after testing.

The disposable D4 data is now removed. The isolated temporary browser profile
used for D4 and D5 is optional local test tooling and may be cleaned up
separately when safe.

## Pending Validation

The hardening smoke tests intentionally did not validate:

- `/api/chat`
- CV upload and `/upload`
- `/stream` and `/resume`
- `/follow-up` and follow-up streaming
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
