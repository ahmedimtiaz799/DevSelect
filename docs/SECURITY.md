# DevSelect Security and Privacy

This document summarizes safeguards present in the repository and the limits of those safeguards. It is not a certification, legal opinion, or claim that AI output should make hiring decisions without human review.

## Security Model

DevSelect separates three trust levels:

1. **Browser:** untrusted input, public Supabase configuration, and a user access token.
2. **FastAPI backend:** verified user identity plus backend-only access to providers, Redis, service-role operations, and workflow checkpoints.
3. **Managed services:** Supabase, Upstash, LlamaParse, AI providers, GitHub, and optional Sentry, each with its own retention and access policy.

The system uses layered controls. Backend authorization does not replace RLS, and RLS does not make service-role code safe by itself.

## Authentication and JWT Validation

- Supabase Auth handles Google/GitHub OAuth and browser sessions.
- Protected FastAPI routes require an `Authorization: Bearer` token.
- JWT algorithms come from a fixed configured asymmetric allowlist; the backend does not trust the unverified token header to choose an algorithm.
- Verification uses the Supabase project's JWKS endpoint.
- Issuer, `authenticated` audience, expiry, issued-at, and subject claims are required.
- The `sub` claim must be a valid UUID and becomes the backend user identity.
- Missing, expired, malformed, wrong-issuer, wrong-audience, unsupported-algorithm, and malformed-subject tokens are covered by deterministic tests.

The browser does not send a trusted `user_id` for backend authorization.

## Chat and Workflow Ownership

Upload, delete, resume, stream, and follow-up routes load the requested chat and verify that its stored `user_id` matches the verified JWT subject.

Resume and stream routes also compare the requested LangGraph `thread_id` with the backend-owned value stored on the chat. Browser roles cannot insert or update `thread_id`, and a unique partial index prevents duplicate non-null thread bindings.

## Supabase RLS and Grants

### Chats

- RLS is enabled.
- The ownership policy requires `user_id = auth.uid()` for reads and writes.
- Anonymous users have no direct table access.
- Authenticated users can select and delete their own chat rows.
- Authenticated inserts are limited to `user_id` and `title`.
- Authenticated updates are limited to `title`, `updated_at`, `is_pinned`, and `pinned_at`.
- Backend-owned fields such as `thread_id`, `candidate_embedding`, `id`, and creation metadata are not browser-writable.

### Messages

- RLS is enabled.
- Ownership is derived through the parent chat using an `EXISTS` policy.
- Authenticated users can read their own chat messages and insert `chat_id`, `role`, and `content`.
- Browser roles cannot update or directly delete message rows.
- Deleting a chat removes associated messages through the reviewed foreign-key cascade.

### Checkpoints

- LangGraph checkpoint tables are backend-only.
- RLS is enabled with no anon/authenticated policies.
- Browser-role grants are revoked.
- The backend uses a private `DATABASE_URL` through `AsyncPostgresSaver`.

Default privileges for future public tables, sequences, and functions are hardened so browser access must be granted intentionally.

See [../supabase/README.md](../supabase/README.md) and the migrations under `supabase/migrations/` for the reviewed SQL history.

## CORS and OAuth

- Production CORS accepts only the origin configured by `FRONTEND_URL`.
- `FRONTEND_URL` must be one origin with no wildcard, credentials, path, query, or fragment; production requires HTTPS.
- Local development additionally permits `localhost:5173` and `127.0.0.1:5173`.
- Allowed methods and headers are narrow: `GET`, `POST`, `OPTIONS`, `Authorization`, and `Content-Type`.
- OAuth `redirectTo` is derived from `window.location.origin` and returns to `/chat`.
- Supabase dashboard Site URL, allowed redirects, and Google/GitHub provider callbacks must still be configured correctly per environment.

## Secrets and Environment Variables

The frontend uses only:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

All private values stay in backend environment variables or deployment secret stores. This includes:

- Supabase service-role and JWT configuration
- direct Postgres connection details
- Upstash credentials
- Gemini/Groq, LlamaParse, GitHub, and Hugging Face credentials
- admin control secret
- optional Sentry DSN

Real `.env` files, backups, dumps, uploads, reports, screenshots, browser profiles, logs, archives, caches, virtual environments, and deployment metadata are excluded through `.gitignore` and `.dockerignore` patterns. Example files must remain placeholder-only.

Secrets should still be scanned in the current tree and Git history before every release. Ignore rules prevent future accidents; they do not erase previously committed data.

## Admin and API Surface

- `/health` is public and returns only stable liveness fields: status and service name.
- Admin routes are disabled unless `ADMIN_ROUTES_ENABLED` is explicitly enabled.
- Enabled admin routes require a minimum-strength non-placeholder secret and use constant-time comparison.
- Production API docs are disabled by default unless `API_DOCS_ENABLED` is explicitly enabled.
- Production startup fails if mock evaluation is enabled.
- Network/platform restrictions should be added around admin routes if they are ever enabled in a public deployment.

## Upload Safety

The CV upload path applies multiple checks before provider calls:

- authenticated JWT and chat ownership
- maximum size of 10 MB
- PDF filename extension and MIME validation
- PDF magic-byte validation
- structural parsing with `pypdf`
- rejection of empty, malformed, encrypted, and over-page-limit PDFs
- configurable CV-likeness checks
- sanitized display filename
- bounded recruiter instruction and preview text
- bounded model input and output settings
- `UploadFile` closure and temporary-file cleanup on success and failure

The raw PDF is processed from bounded memory and temporary storage. It is not stored in Supabase Storage or chat messages. The upload message may retain the sanitized filename and recruiter-entered text.

## CV and Checkpoint Retention

- Raw PDF bytes and preview text are removed from terminal workflow state.
- Completed, failed, stopped, disconnected, and deleted-chat checkpoint threads are purged.
- A periodic TTL task removes abandoned checkpoint threads; the configured default is 24 hours.
- Chat messages retain recruiter text, generated reports, follow-up answers, and upload metadata until the chat is deleted.
- The normal authenticated delete path removes the chat, cascades messages, clears follow-up usage for that evaluation, and purges its workflow thread when present.

LlamaParse and model providers receive CV-derived content during evaluation. Their training, retention, region, and deletion controls are external to this repository and must be reviewed in current provider documentation and dashboards.

## Logging, Errors, and Sentry

- Application logs avoid raw CV text, prompts, provider output, names, GitHub URLs, and full identifiers.
- User, chat, thread, IP, budget, and rate-limit identifiers are hashed before storage or logging where applicable.
- A logging filter redacts bearer tokens, JWTs, common provider-key formats, credential assignments, URLs, query strings, UUIDs, and IPs.
- Uvicorn access logs retain their expected record structure while redacting string fields.
- Expected failures log safe stage, status, code, count, and exception-type metadata rather than raw exception details.
- Public JSON and SSE errors use stable safe messages and codes.
- The frontend maps unknown errors to safe user-facing text and gates diagnostic console output to development.
- Optional Sentry setup disables default PII and scrubs request data, headers, cookies, query strings, user data, breadcrumbs, locals, prompts, CV fields, provider payloads, and URLs.
- Sentinel tests check that representative CV text, tokens, prompts, SQL, paths, URLs, provider output, and thread IDs do not cross public error/logging boundaries.

No redaction system is perfect. Logs and Sentry events should still be sampled and reviewed after deployment without introducing real candidate data into tests.

## Redis Rate, Cost, and Abuse Controls

Upstash Redis provides shared controls for expensive routes:

- token-bucket request limiting with stable hashed user/IP keys
- atomic global daily and monthly evaluation quotas
- atomic per-user daily and lifetime evaluation quotas
- per-evaluation and per-user daily follow-up quotas
- estimated input/output token ceilings
- `SET NX`-style duplicate evaluation locks with TTL
- stream-claim handling to stop duplicate expensive runs
- a circuit flag that can disable AI routes while leaving health checks online
- standardized `429` responses and `Retry-After` where a retry window is meaningful

Current portfolio defaults are intentionally restrictive:

| Control | Default |
| --- | ---: |
| Global evaluations per day | 2 |
| Global evaluations per month | 50 |
| User evaluations per day | 1 |
| User lifetime evaluations | 5 |
| Follow-ups per evaluation | 2 |
| Follow-ups per user per day | 3 |

Production rate, budget, and circuit Redis failures fail closed. Memory fallback is limited to non-production use when enabled.

Application quotas reduce abuse but do not replace provider-side billing alerts, hard spend limits, or account monitoring.

## Safe Error Behavior

- Validation failures return bounded field information, not request bodies.
- Unknown server errors return a generic message.
- Provider and parser failures are mapped to stable public codes.
- SSE errors do not forward raw checkpoint state, provider payloads, prompts, CV text, SQL, stack traces, paths, URLs, or connection details.
- Quota and rate-limit responses expose only the public reason and applicable retry timing.

## Tests and Release Gates

Security-focused backend tests cover:

- JWT and ownership failures
- admin route configuration
- CORS origins
- RLS/grant manual scenarios
- logging and Sentry scrubbing
- upload validation and cleanup
- checkpoint purge/retention
- rate limits, quotas, locks, Redis failures, and provider failures
- JSON/SSE public error safety
- candidate role resolution and follow-up prompt contracts

The manual release process is documented in [../SECURITY_DEPLOYMENT_CHECKLIST.md](../SECURITY_DEPLOYMENT_CHECKLIST.md).

## Known Limitations

- DevSelect is not compliance-certified and does not implement a complete HR data-governance program.
- Human review is required; AI reports can be incomplete, biased, or wrong.
- Message retention is tied to chat deletion rather than a configurable organization policy.
- Provider retention and model-training settings are external controls.
- The backend service-role client has broad privileges by design, so every privileged query requires ownership checks and careful review.
- No dedicated WAF, SIEM, or platform network allowlist is defined in this repository.
- Provider-dashboard spend caps cannot be proven from code.
- Formal dependency scanning and automated CI enforcement are planned rather than currently represented by a checked-in workflow.

## Future Hardening

- Add automated secret, dependency, SAST, migration, and container scans in CI.
- Add organization roles and recruiter-team authorization if multi-user workspaces are introduced.
- Define configurable chat/report retention and deletion SLAs.
- Add audit events that record actions without candidate content.
- Add provider retention attestations and regional data-processing documentation.
- Put enabled admin controls behind platform/network restrictions.
- Add anomaly detection for quota abuse and authentication failures.
- Commission an independent security and bias review before broader hiring use.
