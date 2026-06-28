# DevSelect

DevSelect is a full-stack AI candidate evaluation platform that reviews a candidate CV and GitHub evidence, then generates a structured hiring report with follow-up Q&A.

It is a portfolio project by Ahmed Imtiaz, a Full Stack AI Engineer based in Islamabad/Rawalpindi, Pakistan.

## Live Demo

- Frontend: [https://dev-select.vercel.app](https://dev-select.vercel.app)
- Backend health: [https://devselect-backend.onrender.com/health](https://devselect-backend.onrender.com/health)

> Use only sample or non-sensitive CVs for demo testing. The public portfolio deployment has deliberately strict AI usage limits.

## Why I Built This

Early candidate screening is repetitive and inconsistent. Recruiters often review CVs manually, while public technical evidence such as GitHub is either ignored or judged without a repeatable framework.

DevSelect explores a safer first-pass workflow: extract evidence, review relevant GitHub activity when appropriate, and produce a structured recommendation that a human recruiter can challenge with follow-up questions. The system is designed to assist a hiring decision, not replace one. Authentication, data isolation, bounded uploads, safe logging, and cost controls are part of the product rather than afterthoughts.

## What DevSelect Does

- Provides an authenticated recruiter workflow with Google and GitHub OAuth.
- Accepts and validates PDF CV uploads.
- Extracts structured candidate evidence with an AI-assisted pipeline.
- Reviews GitHub evidence for applicable technical candidates.
- Produces a structured, evidence-grounded hiring recommendation.
- Streams evaluation progress and report text to the browser with SSE.
- Answers follow-up questions from the saved final report context.
- Persists chats, messages, and reports with Supabase Postgres and RLS.
- Supports chat rename, pin, refresh persistence, and safe deletion cleanup.

## Screenshots

Screenshots are planned. To avoid exposing real candidate data, the repository currently includes a privacy-focused screenshot checklist rather than unpublished or placeholder images.

Recommended captures:

1. Landing page in light mode.
2. Chat and generated report in dark mode using a fake CV.
3. A structured report section with all personal data removed.
4. A simple architecture diagram.

See [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) for the safe capture checklist and final file names.

## Architecture Overview

```text
Vercel React Frontend
  |-- Supabase Auth and direct RLS-protected chat persistence
  |-- JWT-authenticated upload, resume, stream, delete, and follow-up requests
  v
FastAPI Backend on Render
  |-- Redis safety layer: rate limits, quotas, circuit state, duplicate locks
  |-- LangGraph evaluation: CV extraction -> optional GitHub review -> report
  |-- Direct Postgres checkpointer for transient workflow state
  v
Supabase Postgres and RLS
  ^
  |-- SSE progress and report streaming back to the frontend
```

For request-level detail, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## System Design

- **Separate frontend and backend:** the browser owns the interaction layer and RLS-protected chat history; FastAPI owns privileged workflow operations and provider calls.
- **FastAPI:** async routes fit upload validation, external API calls, and long-lived SSE responses without introducing a second backend framework.
- **Supabase Auth and RLS:** OAuth sessions identify the recruiter, while database policies and narrowed grants isolate each user's chats and messages.
- **Redis:** Upstash provides shared rate limits, portfolio quotas, duplicate-evaluation locks, and a circuit flag across backend instances.
- **Server-Sent Events:** evaluation output is one-way server-to-browser data, so SSE keeps the protocol simple while supporting progress and incremental report rendering.
- **Backend-only provider keys:** CV parsing, AI models, GitHub access, service-role operations, and checkpoint connections never depend on browser-held secrets.
- **Smoke testing:** staging and production checks cover authentication, RLS reads and writes, backend health, upload, streaming, follow-up persistence, and cleanup.

## AI Workflow

1. **CV upload and validation** - the backend checks authentication, chat ownership, PDF type and structure, size, page count, and CV-likeness before evaluation.
2. **Evidence extraction** - LlamaParse extracts document text and Agent 1 converts bounded evidence into a structured candidate profile.
3. **GitHub review when applicable** - technical profiles with GitHub evidence route through Agent 2. Non-technical or unclear roles can continue with CV-only evidence.
4. **Lead evaluation** - Agent 3 combines the available evidence into a structured report and hiring recommendation.
5. **Follow-up Q&A** - follow-up answers use the persisted final report context; they do not silently rerun the full evaluation.

The workflow is checkpointed in Postgres for interruption and resume behavior. Terminal and stale checkpoints are purged according to the retention logic described in [docs/SECURITY.md](docs/SECURITY.md).

## Security and Privacy

Implemented safeguards include:

- Supabase OAuth sessions and backend JWT verification through project JWKS.
- Required issuer, audience, expiry, issued-at, and UUID subject validation.
- Backend ownership checks for upload, resume, stream, delete, and follow-up routes.
- RLS and column-level grants for user-owned chats and parent-owned messages.
- Browser lockout from internal LangGraph checkpoint tables.
- Production CORS restricted to the configured frontend origin.
- Backend-only service-role, database, Redis, parser, GitHub, and AI credentials.
- PDF size, MIME, magic-byte, structure, encryption, page-count, and CV-likeness checks.
- Log, Sentry, and public-error sanitization for tokens, URLs, identifiers, CV text, prompts, and provider payloads.
- Redis-backed request limits, evaluation/follow-up quotas, duplicate locks, and circuit controls that fail closed in production.
- Temporary PDF cleanup plus terminal and TTL-based checkpoint cleanup.

Generated reports and chat messages remain stored until the user deletes the chat. Third-party provider retention must also be reviewed in each provider dashboard and current policy. DevSelect is not presented as a compliance-certified hiring system.

See [docs/SECURITY.md](docs/SECURITY.md) for the trust boundaries and known limitations.

## Tech Stack

| Area | Technology |
| --- | --- |
| Frontend | React 19, Vite 8, Tailwind CSS, Zustand, React Router |
| Backend | FastAPI, Python 3.12, Uvicorn, Pydantic |
| Auth and database | Supabase Auth, PostgreSQL, Row Level Security |
| AI and agents | LangGraph, Gemini or Groq, LlamaParse, GitHub API |
| Redis and safety | Upstash Redis, token bucket limits, quotas, locks, circuit breaker |
| Deployment | Vercel frontend, Render Docker backend, Supabase, Upstash |
| Testing | Python `unittest`, Node test runner, ESLint, Vite production build |

## Local Development

### Prerequisites

- Python 3.12
- Node.js compatible with Vite 8
- A separate Supabase development project
- An Upstash Redis database
- Provider credentials for the evaluation features you intend to test

### 1. Clone and configure

```powershell
git clone <repository-url>
cd devselect

Copy-Item frontend/.env.example frontend/.env
Copy-Item backend/.env.example backend/.env
```

Fill the local files privately. Never use production credentials for routine local development.

### 2. Start the frontend

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

### 3. Start the backend

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r app/requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Normal backend startup opens the Postgres checkpoint pool and runs the LangGraph checkpointer setup. Use a reviewed development database, not production.

### 4. Database setup

Read [supabase/README.md](supabase/README.md) before applying any SQL. The staging initializer is not a production migration, and every hardening migration should be reviewed against the target schema first.

## Environment Variables

Use the checked-in example files as the source of truth:

- Frontend: [`frontend/.env.example`](frontend/.env.example)
- Backend: [`backend/.env.example`](backend/.env.example)

### Frontend public configuration

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

These values are bundled into the browser and must never contain private credentials.

### Backend private configuration

Core application and security:

- `APP_ENV`
- `FRONTEND_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_JWT_ALGORITHMS`
- `SUPABASE_JWT_AUDIENCE`
- `DATABASE_URL`

Providers and models:

- `AI_PROVIDER`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `LLAMAPARSE_API_KEY`
- `HUGGINGFACE_API_TOKEN`
- `GITHUB_TOKEN`
- `AGENT1_MODEL`
- `AGENT2_MODEL`
- `AGENT3_MODEL`
- `AGENT3_FALLBACK_MODEL`
- `FOLLOW_UP_MODEL`

Redis, quotas, and operational controls:

- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `DAILY_BUDGET_ENABLED`
- `GLOBAL_EVALS_PER_DAY`
- `GLOBAL_EVALS_PER_MONTH`
- `USER_EVALS_PER_DAY`
- `USER_EVALS_LIFETIME`
- `FOLLOWUPS_PER_EVALUATION`
- `FOLLOWUPS_PER_USER_DAY`
- `EVALUATION_LOCK_TTL_SECONDS`
- `RATE_LIMIT_FAIL_OPEN`
- `CIRCUIT_BREAKER_FAIL_OPEN`
- `BUDGET_REDIS_FALLBACK_ENABLED`
- `ADMIN_ROUTES_ENABLED`
- `ADMIN_SECRET`
- `API_DOCS_ENABLED`
- `DEV_MOCK_EVALUATION`
- `SENTRY_DSN`

Input, output, timeout, and retention limits are also documented in `backend/.env.example`. Never commit real `.env` files.

## Testing and Validation

Backend tests are deterministic and do not require paid provider calls:

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm test
npm run build
```

The project has also completed controlled deployment smoke tests for backend health, OAuth and session refresh, RLS-protected chat reads/writes, one sample CV evaluation, SSE completion, one follow-up, persistence after refresh, and UI-based cleanup. The test used disposable data and checked that sensitive CV text, tokens, and provider payloads were not emitted through application logs or public errors.

The release gate is documented in [SECURITY_DEPLOYMENT_CHECKLIST.md](SECURITY_DEPLOYMENT_CHECKLIST.md).

## Deployment

- **Frontend:** Vercel builds the `frontend` Vite application and serves BrowserRouter routes through the SPA rewrite in `frontend/vercel.json`.
- **Backend:** Render builds `backend/Dockerfile`, runs one non-root Uvicorn worker, and exposes the minimal `/health` endpoint.
- **Auth and data:** Supabase hosts OAuth, Postgres, RLS policies, and LangGraph checkpoint tables.
- **Safety state:** Upstash Redis stores shared request limits, quotas, duplicate locks, and the AI circuit flag.
- **Validation:** changes are staged first, followed by a small production health/auth/read test and an explicitly approved evaluation test.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for configuration and rollback guidance.

## Known Limitations

- The public portfolio deployment has strict daily, monthly, per-user, and follow-up quotas.
- Demo users should upload only fake, sample, or otherwise non-sensitive CVs.
- Application-level quotas are implemented, but provider-dashboard billing caps and retention controls remain deployment-owner responsibilities.
- Evaluations currently run inside the web service process; there is no separate durable job queue or worker tier.
- Automated GitHub Actions CI/CD is planned; the repository currently provides a documented manual release gate.
- Sentry integration is optional, and a dedicated production observability dashboard is not included.
- Long-term object storage is intentionally not used for uploaded PDFs. A future storage feature would require an explicit retention and deletion policy.
- AI output is a screening aid and can be incomplete or wrong. A human must make the hiring decision.

## Future Improvements

- Add GitHub Actions for tests, builds, secret scanning, and migration checks.
- Move long evaluations to a durable queue and worker architecture.
- Add Langfuse, LangSmith, or OpenTelemetry traces with the same PII controls.
- Add a custom Supabase auth domain and production branding.
- Build golden evaluation datasets and model-regression scoring.
- Add production dashboards for latency, errors, quota usage, and provider health.
- Introduce object storage only if product requirements justify it and retention is defined.
- Add privacy-safe recruiter demo analytics and funnel metrics.

## Engineering Highlights

- Separates browser-safe Supabase access from privileged backend operations, with JWT ownership checks and RLS as independent authorization layers.
- Uses SSE for efficient one-way delivery of evaluation progress and incremental report content without unnecessary WebSocket complexity.
- Routes candidates through a conditional LangGraph workflow that skips GitHub analysis when it is not relevant to the candidate domain.
- Applies atomic Redis quotas, follow-up limits, duplicate-evaluation locks, token-bucket rate limiting, and circuit controls to protect provider cost and availability.
- Validates uploads in layers and removes raw PDFs and transient checkpoint evidence after processing.
- Treats logging and public errors as data-loss surfaces through identifier hashing, Sentry scrubbing, and sentinel leakage tests.
- Diagnoses production network failures through separate CORS/preflight, upload-acceptance, and SSE-startup signals without logging sensitive payloads.
- Validates database changes in staging before main using backups, RLS tests, backend health checks, frontend smoke tests, and UI cleanup.
- Packages FastAPI as a non-root, one-worker Docker service with production-specific CORS, API-doc, and admin-route controls.
- Documents the main scaling boundary clearly: long-running AI evaluation should move to durable workers before serving high concurrency.

## License

No open-source license has been added yet. All rights reserved by default.
