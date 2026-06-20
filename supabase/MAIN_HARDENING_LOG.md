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

## D6 Controlled Evaluation Validation

### Operations and Supply Chain CV

- The candidate was identified as Muhammad Saad Khan.
- DevSelect detected the role as Operations and Supply Chain Coordinator at
  junior seniority and recommended Proceed to Interview.
- The CV's operations, supply chain, procurement, inventory, and logistics
  evidence determined the role.
- A short Volunteer Trainer entry did not override the stronger role evidence.
- The chat header showed the correct role.
- The non-technical/business operations path completed without visible GitHub
  confusion in the report.

### Technical CV With GitHub Selection

- The candidate was identified as Ayan Raza and the role as Junior Full Stack
  AI Engineer.
- The CV contained two GitHub URLs, and the profile selector and manual profile
  selection flow worked.
- The selected profile was evaluated successfully.
- DevSelect recommended No Hire because the selected profile was clearly
  inconsistent with the CV's React, FastAPI, Python, and AI claims.
- The mismatch combined a clearly wrong/famous-person profile with unrelated
  Linux, C, Assembly, and systems-programming evidence.
- This validated that a famous or technically strong profile is not rewarded
  when its identity and technical evidence materially contradict the CV.

### Follow-Up Evidence-Scope Fix

The first CV-only follow-up answer incorrectly reused the GitHub mismatch after
the recruiter explicitly asked to ignore GitHub. Inspection found that the
persisted-report follow-up prompt was over-anchored to the saved recommendation
and had no counterfactual evidence-scope rules.

The prompt-only fix:

- added scoped/counterfactual evidence instructions
- requires excluded evidence to remain excluded from the hypothetical answer
- allows a hypothetical recommendation to differ from the persisted report
- preserves the persisted final report as the official full-scope result
- treats a GitHub name-only mismatch as a verification note rather than an
  automatic No Hire
- preserves a major red flag for a clearly wrong/famous-person profile when
  repository, language, project, or identity evidence materially contradicts
  the CV

Four deterministic prompt-contract tests passed. Agent 1, Agent 2, Agent 3,
frontend behavior, report format, and the persisted-report follow-up
architecture were unchanged. No full evaluation reload or rerun logic was
added.

The manual retest passed:

- backend `/health` returned 200
- one follow-up request completed normally over SSE
- no new upload, evaluation stream, or resume request occurred
- no provider quota error occurred
- the CV-only hypothetical softened to Potential Hire with reservations /
  Consider for Interview
- the answer did not use the excluded GitHub mismatch as its CV-only reason
- the original No Hire remained applicable when the selected GitHub profile
  was included

During D7A, the corrected follow-up answer was confirmed to remain persisted
after a fresh app load.

## D7 Disposable Test Chat Cleanup

D7A identified exactly five disposable D6 chats:

1. the failed-CORS `Operations_Supply_Chain_Test_CV` chat
2. the completed Muhammad Saad Khan Operations and Supply Chain report
3. the Muhammad Saad Khan Gemini-overload attempt
4. the Muhammad Saad Khan Groq-rate-limit attempt
5. the Ayan Raza technical GitHub-selector report and follow-up chat

D7B deleted exactly those five chats through the normal authenticated sidebar
menu and delete confirmation modal:

- each chat's persisted content was verified immediately before deletion
- all five `DELETE /rest/v1/chats` requests returned 204
- the sidebar count decreased from 57 to 52
- refresh confirmed that none of the deleted chats returned
- representative non-D6 chats remained present
- no uncertain chat was deleted
- no upload, evaluation, stream, resume, follow-up, or AI/provider call occurred
- no SQL, service-role deletion, or manual database mutation was used
- no project files changed during cleanup, and Git remained clean

D6 validation and its disposable-data cleanup are complete.

## Pending Validation

The following items remain pending:

- broader regression coverage across additional CV and provider scenarios
- deployment preparation, deployment prompt files, and post-deployment
  monitoring

The D6 Operations and technical GitHub-selector flows validated controlled CV
upload, evaluation, SSE completion, report generation, profile selection, and
the relevant LlamaParse, Gemini, and GitHub-backed paths. This does not replace
broader regression, quota, failure-mode, or deployment validation.

The next phase is deployment preparation.

## Non-Blocking Warning

A small Supabase auth device clock-skew warning appeared during the frontend
test. It did not block sign-in, reads, or session persistence. Sync Windows
system time before further authentication testing.

## Rollback

No rollback was needed.
