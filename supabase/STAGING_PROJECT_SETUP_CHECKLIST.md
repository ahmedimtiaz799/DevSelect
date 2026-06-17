# DevSelect Staging Supabase Project Setup Checklist

Use this checklist before applying any D1 Supabase hardening SQL.

Do not use the production/main Supabase project as staging.

## Goal

Create or confirm a separate Supabase staging environment for DevSelect so D1
grant/index hardening can be tested without touching production data.

## Before You Start

- Do not run D1 migrations yet.
- Do not run Supabase CLI commands yet.
- Do not paste secrets into docs, ChatGPT, Codex, GitHub, README files,
  screenshots, or commits.
- Do not modify production env files.
- Do not use real candidate CV data for setup or RLS testing.
- Keep real staging env values outside Git.

## Option A: Supabase Branching, If Available

Supabase branching can create an isolated environment from the main project.
Use this only if your Supabase plan/project supports it.

Baby steps:

1. Open the Supabase dashboard.
2. Confirm you are looking at the correct main DevSelect project.
3. Check whether Supabase Branching is available.
4. Create a new branch for staging or testing.
5. Name it clearly, for example `devselect-staging`.
6. Confirm the branch has its own API URL, anon key, service role key, and
   database connection details.
7. Confirm this branch is not the production/main branch.
8. Do not apply D1 SQL yet.
9. Store branch/staging values only in private local env files or your deployment
   secret manager.

Copy into backend staging env outside Git:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- staging Redis values, if used
- staging provider keys, if used
- staging `FRONTEND_URL`

Copy into frontend staging env outside Git:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

Do not put service role keys or `DATABASE_URL` in frontend env.

## Option B: Separate Supabase Staging/Test Project

Use this option if branching is not available or if you want the cleanest
separation.

Baby steps:

1. Open the Supabase dashboard.
2. Create a new Supabase project.
3. Name it clearly, for example `DevSelect Staging` or `DevSelect Test`.
4. Do not use the production/main project.
5. Choose a sensible region and plan for temporary testing.
6. Configure Auth providers only with staging callback URLs.
7. Do not use production callback URLs for staging auth.
8. Do not apply D1 SQL yet.
9. Configure the staging database/schema later from the reviewed baseline and
   migrations.
10. Store staging backend env values outside Git.
11. Store staging frontend env values outside Git.

Backend staging env should use staging-only values for:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- Redis or Upstash, if used
- provider keys, if used
- `FRONTEND_URL`

Frontend staging env should use only:

- staging Supabase URL
- staging Supabase anon key
- staging backend/API origin

## What Not To Do

- Do not paste secrets into docs, ChatGPT, Codex, GitHub, README files,
  screenshots, or commits.
- Do not copy production keys into staging env.
- Do not apply `001_harden_table_grants.sql` or `002_add_core_indexes.sql`
  until staging identity is confirmed.
- Do not run RLS user-behavior tests with service role.
- Do not put service role keys in frontend env.
- Do not put `DATABASE_URL` in frontend env.
- Do not test with real candidate CV data unless a reviewed staging data policy
  allows it.
- Do not treat a production branch/project as staging.

## Verification Checklist

Before the first D1 staging migration, confirm:

- Staging Supabase identity is confirmed.
- Staging project or branch is different from production/main.
- Staging values are stored only in local real env files or deployment secret
  manager.
- Example env files remain placeholder-only.
- `backend/.env.staging` is ignored by Git.
- `frontend/.env.staging` is ignored by Git.
- Frontend staging points to the staging backend/API.
- Frontend staging uses only the staging Supabase anon key.
- Backend staging points to the staging Supabase URL.
- Backend staging uses the staging service role key.
- Backend staging uses the staging database connection.
- Backend staging uses staging Redis/provider keys where possible.
- Production env files remain untouched.
- No D1 migration has been applied yet.
- No production data is required for testing.

## Final Decision Gate

- If staging exists and env separation is configured: next step is D1-K staging
  apply checklist.
- If staging does not exist: create a separate Supabase staging project first.
- If only production exists: stop.
- If you are unsure which project is production: stop and ask.

## Files To Use Next

After staging identity and env separation are confirmed:

- Read `supabase/STAGING_RLS_TEST_PLAN.md`.
- Review `supabase/migrations/001_harden_table_grants.sql`.
- Review `supabase/migrations/002_add_core_indexes.sql`.
- Run `supabase/rls_manual_tests.sql` only manually, only in staging, and not
  with service-role context.
