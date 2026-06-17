# DevSelect D1 Staging Strategy

This document decides the safe staging strategy before applying any Supabase
hardening SQL.

Do not apply the D1 hardening drafts to production first.

## Current Local Evidence

- Local backend env files exist:
  - `backend/.env`
  - `backend/.env.example`
  - `backend/.env.staging.example`
- Local frontend env files exist:
  - `frontend/.env`
  - `frontend/.env.example`
  - `frontend/.env.staging.example`
- Staging example files exist locally, but no real staging env file should be
  committed.
- No separate production env file was found locally.
- No Supabase CLI config file was found locally.
- The env examples document one Supabase variable set, not separate staging and
  production variable groups.
- Supabase docs currently mention staging in:
  - `supabase/README.md`
  - `supabase/STAGING_RLS_TEST_PLAN.md`

Because local env values were not inspected or printed, this repo evidence can
only prove that one Supabase configuration shape exists locally. It cannot prove
whether the configured project is development, staging, or production.

## Recommended Staging Option

Use Option B unless a separate staging Supabase project already exists outside
the repo.

### Option A: Existing Separate Staging Project

Local evidence: not found.

If a separate staging project exists outside the repo, the safest next step is
to configure staging-only environment variables outside Git, then run the
staging apply checklist from `STAGING_RLS_TEST_PLAN.md`.

### Option B: Create A Separate Staging Project

Recommended default.

Create a separate Supabase test/staging project before applying:

- `supabase/migrations/001_harden_table_grants.sql`
- `supabase/migrations/002_add_core_indexes.sql`

The staging project should use disposable data or a controlled sanitized copy.
Do not require real candidate CV data for RLS testing.

### Option C: Use Production As Staging

Blocked and not recommended.

Do not apply D1 hardening drafts first to the project that holds real users,
real chats, real candidate CV content, or production provider flows.

### Option D: Use Local Supabase CLI

Useful only for schema-shape practice and SQL syntax review if the local schema
is recreated accurately.

Limitations:

- It does not prove hosted Supabase project grants match production/staging.
- It does not prove hosted auth JWT behavior.
- It does not prove hosted PostgREST behavior with current policies.
- It does not prove FastAPI checkpoint behavior against the hosted database.
- It does not replace staging RLS and backend smoke tests.

## Must Exist Before Applying 001 And 002

- Separate Supabase staging project, or explicit proof that an existing project
  is disposable staging.
- Staging backend env values stored outside Git.
- Staging frontend env values stored outside Git.
- Staging database backup/export.
- Confirmed table names and columns match
  `supabase/migrations/000_baseline_current_schema.sql`.
- Confirmed `public.chats` and `public.messages` RLS policies exist.
- Confirmed checkpoint tables are backend-only.
- Confirmed FastAPI staging deployment can use a backend-only privileged
  database connection for LangGraph checkpoints.
- Current local D1 draft files committed before staging work starts.

## Environment Separation Checklist

- Backend staging env has its own Supabase project variables.
- Frontend staging env has its own Supabase anon project variables.
- Backend staging service role key is never copied into frontend env.
- Backend staging database URL is never copied into frontend env.
- Production env values are not reused for staging tests.
- Staging provider keys and Redis values are separate where possible.
- `.env`, `.env.local`, `.env.staging`, `.env.production`, and local variants
  remain uncommitted.
- Staging secrets are stored in the hosting platform or local private env files,
  not in Git.
- `backend/.env.staging.example` and `frontend/.env.staging.example` are
  placeholder-only templates, not real secrets.

## Never Use Production First

Stop if any of these are true:

- Only one Supabase project exists.
- You are unsure whether the current project contains production data.
- The target project contains real candidate CVs or real user chats.
- You cannot verify staging env values are separate.
- You cannot rollback safely.

## Safe Setup Checklist For A Staging Project

1. Create or identify a separate Supabase staging project.
2. Store staging backend env values outside Git.
3. Store staging frontend env values outside Git.
4. Export current staging schema before changes.
5. Confirm the schema matches the local baseline snapshot.
6. Confirm staging has no real candidate CV data.
7. Apply `001_harden_table_grants.sql` only to staging.
8. Apply `002_add_core_indexes.sql` only to staging.
9. Run manual RLS tests without service-role context.
10. Run frontend login and chat-history smoke tests.
11. Run backend evaluation/checkpoint smoke tests.
12. Record failures and rollback notes before any production discussion.

## What Not To Copy Into Git

- Supabase service role keys.
- Supabase anon key values.
- JWT secrets.
- Database URLs or Postgres passwords.
- Provider API keys.
- Redis or Upstash URLs/tokens.
- Sentry DSNs.
- Real user IDs.
- Candidate CV data.
- Generated reports from real candidates.

## Manual Verification Before First Staging Migration

- Confirm target project is staging, not production.
- Confirm backup/export exists.
- Confirm `public.chats` exists.
- Confirm `public.messages` exists.
- Confirm all checkpoint tables exist.
- Confirm `chats.user_id` exists.
- Confirm `chats.updated_at` exists.
- Confirm `messages.chat_id` exists.
- Confirm `messages.created_at` exists.
- Confirm `messages(role, content, chat_id)` insert shape still works.
- Confirm current RLS policies match the baseline snapshot.
- Confirm checkpoint tables have no anon/authenticated user policies.
- Confirm staging backend can connect with its backend-only database URL.

## Decision Gate

- If staging exists: prepare and run the staging apply checklist next.
- If staging does not exist: create a separate Supabase staging project first.
- If only production exists: stop.

## Final Recommendation

Do not apply D1 hardening SQL until a separate staging Supabase project is
confirmed and configured. The safest next real action is staging setup, not SQL
execution.
