# DevSelect Security Deployment Checklist

Use this checklist for every release candidate. A failed required check blocks
deployment until it is fixed or a documented security review explicitly accepts
the risk.

## 1. Deterministic Local Checks

Run from a clean working tree using the supported Python and Node versions.

### Backend

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests
```

Expected: all tests pass without external provider calls.

### Frontend

```powershell
cd frontend
npm ci
npm run lint
npm test
npm run build
```

Expected: lint, tests, and the production build pass. Build-size warnings should
be reviewed but do not block unless they indicate a functional or operational
limit.

## 2. Secret and Artifact Gate

- Run a repository and Git-history scan with a dedicated scanner such as
  Gitleaks before deployment.
- Block deployment for any unresolved credential, private key, connection
  string, JWT, provider token, or sensitive candidate artifact.
- Review scanner suppressions individually. Do not suppress an entire path
  merely because it contains examples.
- Confirm real `.env` files, dumps, reports, CVs, screenshots, browser profiles,
  test results, and deployment metadata remain ignored and untracked.
- Confirm `.dockerignore` excludes the same private and generated artifacts
  before any future container build.

## 3. Environment Example Parity

- Compare `backend/app/config.py` settings with:
  - `backend/.env.example`
  - `backend/.env.staging.example`
- Confirm every backend setting is documented and no obsolete variable remains.
- Compare frontend `import.meta.env.VITE_*` usage with:
  - `frontend/.env.example`
  - `frontend/.env.staging.example`
- Frontend examples may contain only public `VITE_*` configuration.
- All example values must remain empty or clearly placeholder-only.
- Validate production configuration without printing values:
  - production frontend origin uses HTTPS and contains no path or wildcard
  - admin and API docs flags have production-safe values
  - mock evaluation is disabled
  - Redis-backed quota controls fail closed
  - JWT algorithm, issuer source, and audience match the production Supabase
    project

## 4. Migration and RLS Gate

- Review every new migration for destructive or data-copying SQL.
- Confirm local and staging migration history are aligned before promotion.
- Apply new migrations to the separate staging project first.
- Run `supabase/rls_manual_tests.sql` only in the documented staging context,
  never with service role as the user-RLS test context.
- Verify:
  - anonymous users cannot access private app data
  - users cannot read or write another user's chats or messages
  - browser roles cannot write backend-owned chat columns
  - checkpoint tables remain unavailable to browser roles
  - backend checkpoint startup still succeeds
- Take a reviewed backup/export before any production migration.
- Do not apply the staging-only schema initialization migration to an existing
  production schema.

## 5. Staging Smoke Tests

Use staging-only environment files and disposable test users/data.

1. Backend starts with normal lifespan and `/health` returns `200`.
2. Frontend production build loads.
3. OAuth sign-in returns to the expected authenticated route.
4. Session and sidebar/history reads survive refresh.
5. Chat create, message persistence, rename, pin/unpin, and delete work under RLS.
6. One approved disposable CV validates upload, SSE completion, final report
   persistence, and checkpoint cleanup.
7. GitHub selection and resume are tested only with an approved test CV.
8. Follow-up limits and persistence are verified.
9. Invalid files, cross-user access, duplicate evaluation, quotas, circuit-open,
   provider failure, and sanitized error paths behave as expected.
10. Logs and Sentry events contain no CV text, tokens, prompts, provider
    payloads, private URLs, or raw exception details.
11. Delete all disposable test chats through the normal authenticated UI path.

## 6. Production Approval Criteria

Deployment requires:

- clean Git status and reviewed commit
- deterministic backend and frontend checks passing
- no unresolved high-confidence secret finding
- environment parity and production-safe flags confirmed
- staging migrations, RLS tests, and smoke tests passing
- production backup and rollback steps prepared
- expected Supabase, OAuth, Redis, provider, and monitoring configuration
  confirmed without exposing values
- an identified release owner and rollback decision maker

## 7. Post-Deployment Smoke Tests

Run the smallest safe production checks:

1. `/health` returns `200` with minimal output.
2. Production frontend loads over HTTPS.
3. OAuth sign-in, session refresh, chat history read, and one existing chat read
   succeed.
4. Confirm no CORS, JWT, RLS, checkpoint, Redis, quota, or provider errors.
5. Run write/evaluation smoke tests only when explicitly approved and within
   quota.
6. Verify error monitoring receives sanitized operational events.
7. Confirm no staging, localhost, preview, or wildcard URL is accepted by
   production CORS or OAuth configuration.

## 8. Stop and Rollback Conditions

Stop deployment or begin the reviewed rollback when any of these occurs:

- migration history or target project identity is uncertain
- backup/export is missing
- authentication, RLS, checkpoint startup, or chat persistence regresses
- secrets or private candidate data appear in artifacts, logs, or responses
- unexpected destructive SQL or data loss is observed
- production returns repeated `401`, `403`, `429`, or `5xx` responses outside
  the expected tested behavior
- duplicate evaluations bypass locks or quotas fail open
- provider cost, circuit-breaker, or Redis behavior is uncontrolled

Collect logs and exact failing stages before rollback. Do not broaden grants,
disable RLS, expose admin routes, or bypass quota controls as an emergency fix.
