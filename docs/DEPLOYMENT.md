# DevSelect Deployment

DevSelect uses four managed deployment boundaries:

- Vercel for the React/Vite frontend
- Render for the Dockerized FastAPI backend
- Supabase for Auth and Postgres
- Upstash for Redis-backed safety controls

This document is an operational summary, not an automated deployment script. Never paste secrets into documentation, issues, screenshots, or command output.

## Environments

Keep local/development, staging, and production separate.

| Environment | Purpose | Data rule |
| --- | --- | --- |
| Local/development | Fast feedback and deterministic tests | Use fake data and non-production services |
| Staging | Migration, RLS, OAuth, upload, stream, and failure-path validation | Disposable users and sample CVs only |
| Production | Public portfolio demo | Sample/non-sensitive CVs and strict quotas |

Production credentials must never be copied into local example files. The repository includes staging strategy and migration checklists under `supabase/`.

## Frontend on Vercel

Recommended settings:

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Framework | Vite |
| Install command | `npm install` or platform default |
| Build command | `npm run build` |
| Output directory | `dist` |

Required public environment variable names:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

The frontend uses `BrowserRouter`. `frontend/vercel.json` rewrites all routes to `index.html` so direct visits and refreshes on `/chat`, `/pricing`, `/about`, `/terms`, and `/privacy` work.

The current public frontend is [https://dev-select.vercel.app](https://dev-select.vercel.app).

## Backend Docker Image

`backend/Dockerfile` uses:

- a pinned Python 3.12 slim base
- dependencies from `backend/app/requirements.txt`
- a non-root `devselect` user
- a writable application temp directory
- one Uvicorn worker
- `PORT` supplied by the platform, defaulting to `8000`

Build from the repository root:

```powershell
docker build -t devselect-backend:local backend
```

Run with a private local environment file:

```powershell
docker run --rm --name devselect-backend -p 8000:8000 --env-file backend/.env devselect-backend:local
```

Check liveness:

```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
```

Local Docker verification was skipped on the original low-resource Windows development machine. The Render cloud build became the Docker build/startup verification path.

## Backend on Render

Recommended service shape:

- Web Service
- Docker runtime
- repository root connected to the reviewed deployment branch
- Dockerfile at `backend/Dockerfile`
- health check path `/health`
- secrets entered through Render environment settings, never build arguments

The image starts:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

Proxy headers are enabled, and trusted forwarded IP behavior is controlled by `FORWARDED_ALLOW_IPS` at runtime. Review that value for the current Render proxy model instead of using an unrestricted value by habit.

The current public health endpoint is [https://devselect-backend.onrender.com/health](https://devselect-backend.onrender.com/health). It intentionally returns only stable status and service fields.

### Backend environment groups

Use [`../backend/.env.example`](../backend/.env.example) as the exact application-variable inventory. Main groups are:

- runtime: `APP_ENV`, `FRONTEND_URL`
- Supabase/JWT: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_JWT_ALGORITHMS`, `SUPABASE_JWT_AUDIENCE`
- Postgres: `DATABASE_URL`
- providers: `AI_PROVIDER`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `LLAMAPARSE_API_KEY`, `HUGGINGFACE_API_TOKEN`, `GITHUB_TOKEN`, model names
- Redis: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
- safety controls: quota, token, timeout, upload, retention, and lock variables
- operations: `ADMIN_ROUTES_ENABLED`, `ADMIN_SECRET`, `API_DOCS_ENABLED`, `DEV_MOCK_EVALUATION`, `SENTRY_DSN`

The Docker command also accepts `FORWARDED_ALLOW_IPS` for Uvicorn proxy trust. It is a container/runtime setting rather than a Pydantic application setting and is not currently listed in `backend/.env.example`.

Production-safe configuration should keep admin routes and mock evaluation disabled, docs disabled unless explicitly needed, strict Redis fail-closed behavior, and `FRONTEND_URL` set to the exact HTTPS frontend origin.

### Startup behavior

FastAPI startup:

1. validates configuration
2. initializes optional sanitized Sentry reporting
3. opens the async Postgres checkpoint pool
4. runs `AsyncPostgresSaver.setup()`
5. compiles the LangGraph workflow with the checkpointer
6. starts the checkpoint TTL cleanup loop

This means a valid `DATABASE_URL` and compatible checkpoint permissions are boot requirements, not only evaluation-time requirements.

## Supabase

Supabase provides OAuth, user sessions, Postgres, RLS, and checkpoint storage.

Before changing schema or grants:

1. identify the target project without printing its reference
2. export/backup the target state
3. apply to staging first
4. run RLS and backend startup tests
5. review migration history alignment
6. schedule a separate production apply session and rollback decision

Important migration boundary:

- `000_init_devselect_staging_schema.sql` initializes an empty staging project and is not for an existing production schema.
- hardening migrations must be reviewed against the current target before use.

Read [`../supabase/README.md`](../supabase/README.md) and [`../supabase/STAGING_APPLY_CHECKLIST.md`](../supabase/STAGING_APPLY_CHECKLIST.md) before applying SQL.

## OAuth URL Configuration

For each Supabase environment:

- **Site URL:** the deployed frontend origin
- **Additional redirect URL:** the deployed frontend `/chat` route
- **Google callback:** the environment's Supabase `/auth/v1/callback`
- **GitHub callback:** the environment's Supabase `/auth/v1/callback`

The provider callback is Supabase, not the FastAPI backend. The browser's `redirectTo` is `${window.location.origin}/chat`, so local, staging, and production origins must be explicitly allowed in the matching Supabase project.

Do not leave localhost, preview deployments, stale domains, or unrelated origins in a production allowlist without a documented reason.

See [`../supabase/OAUTH_URL_CHECKLIST.md`](../supabase/OAUTH_URL_CHECKLIST.md).

## Upstash Redis

Production requires private Upstash REST URL/token settings. Redis enforces:

- request token buckets
- evaluation and follow-up quotas
- estimated token budgets
- duplicate evaluation locks
- stream claims
- the AI circuit flag

Production is designed to fail closed when Redis cannot enforce rate, budget, or circuit controls. A Redis outage can therefore leave `/health` available while protected AI routes return safe `503` responses.

Use a separate staging Redis database where possible. Reusing production Redis for staging mixes counters, locks, and circuit state.

## Pre-Deployment Checks

From a clean working tree:

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests

cd ..\frontend
npm ci
npm run lint
npm test
npm run build
```

Also complete:

- secret and Git-history scan
- environment-example parity review
- staging migration/RLS validation
- staging OAuth and session refresh
- one approved disposable upload/stream/follow-up test
- log and Sentry leakage review
- cleanup of all disposable test chats

The complete gate is in [`../SECURITY_DEPLOYMENT_CHECKLIST.md`](../SECURITY_DEPLOYMENT_CHECKLIST.md).

## Post-Deployment Smoke Test

Run from lowest risk to highest:

1. Backend `/health` returns `200` with minimal output.
2. Frontend loads over HTTPS and direct route refresh works.
3. Google/GitHub OAuth returns to `/chat`.
4. Session refresh and chat-history reads work.
5. Create, rename, pin/unpin, and delete a disposable chat under RLS.
6. Confirm browser/backend logs have no unexpected `401`, `403`, `429`, or `5xx` responses.
7. Only with explicit approval and available quota, upload one sample PDF.
8. Confirm one `/upload`, one stream, normal SSE completion, final report persistence, and no duplicate evaluation.
9. Ask one bounded follow-up and verify persistence.
10. Delete the disposable chat through the normal UI and verify it does not return.
11. Review sanitized logs and optional Sentry events.

Do not use a real candidate CV for deployment testing.

## Rollback Thinking

Prepare rollback before deploying:

- record the current frontend and backend commit/deployment IDs
- retain a reviewed database backup before migrations
- know which owner can stop or roll back the release
- keep schema rollback separate from application rollback
- collect the failing stage and sanitized logs before changing grants or policies

Stop or roll back when:

- target environment identity is uncertain
- authentication or RLS isolation regresses
- checkpoint startup fails
- chat persistence or deletion breaks
- private candidate data or credentials appear in logs/responses
- duplicate evaluations bypass locks
- quotas or circuit controls fail open
- provider spend or error rates become uncontrolled

Never restore service by broadly granting tables, disabling RLS, exposing admin routes, or bypassing quotas.

## Common Deployment Failures

### Frontend reports `Failed to fetch`

Check, in order:

1. frontend `VITE_API_URL`
2. backend availability and `/health`
3. exact production `FRONTEND_URL`
4. CORS preflight status
5. browser network stage: upload request versus SSE startup

Do not log request bodies, access tokens, resume payloads, or private query strings while diagnosing.

### OAuth returns to localhost

Review Supabase Site URL and Additional Redirect URLs, then review Google/GitHub callback configuration. The frontend already derives its redirect from the current browser origin.

### Backend exits during startup

Check safe error types for:

- missing required settings
- invalid production `FRONTEND_URL`
- invalid admin secret when admin routes are enabled
- mock evaluation enabled in production
- Postgres/checkpointer connection or permission failure

### AI routes return `429`

This is expected when portfolio quotas or request rate limits are reached. Respect `Retry-After`; do not retry in a tight loop or raise limits without a cost review.

### AI routes return `503` while health is green

Check Redis reachability, the circuit flag, checkpoint state, and provider availability. The system intentionally keeps liveness separate from expensive-route readiness.

### Stream ends without a report

Inspect sanitized upload/stream stage markers, provider status class, and checkpoint availability. The frontend maps unexpected termination to a stable public error and should not persist an empty report.
