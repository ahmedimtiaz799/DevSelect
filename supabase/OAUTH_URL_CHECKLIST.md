# DevSelect OAuth URL Checklist

Use exact environment-specific URLs. Do not copy production URLs or credentials
into staging, and do not use wildcard production redirects.

No dashboard setting is changed by this document.

## Per Environment

For local, staging, and production, confirm all of the following before testing
OAuth:

1. Frontend environment points to the matching Supabase project and backend.
2. Backend `FRONTEND_URL` is the exact frontend origin only:
   - no `/chat` path
   - no query or fragment
   - no wildcard
   - HTTPS for production
3. Supabase Auth **Site URL** equals the deployed frontend origin.
4. Supabase Auth **Additional Redirect URLs** includes the exact frontend URL
   ending in `/chat`.
5. The OAuth provider callback points to the matching Supabase project, not
   directly to the frontend.

## Expected URL Shapes

| Setting | Expected shape |
| --- | --- |
| Backend `FRONTEND_URL` | `https://<frontend-domain>` |
| Frontend `VITE_API_URL` | `https://<backend-domain>` |
| Supabase Site URL | `https://<frontend-domain>` |
| Supabase Additional Redirect URL | `https://<frontend-domain>/chat` |
| Google authorized redirect URI | `https://<project-ref>.supabase.co/auth/v1/callback` |
| GitHub OAuth callback URL | `https://<project-ref>.supabase.co/auth/v1/callback` |

The frontend derives `redirectTo` from the current browser origin and appends
`/chat`. The exact result must be allowed by the matching Supabase project.

## Local Development

Allow only the loopback URL actually used during local testing, for example:

- `http://localhost:5173/chat`
- `http://127.0.0.1:5173/chat`

If both host forms are used, list both explicitly in the non-production
Supabase project. Do not carry loopback URLs into production CORS.

## Staging

- Use a separate Supabase staging project or branch.
- Use the staging frontend origin for Site URL.
- Allow the exact staging frontend `/chat` redirect.
- Configure Google/GitHub with the staging Supabase callback.
- Keep preview URLs explicit; do not add a broad wildcard to production.

## Production Gate

Before deployment, manually verify:

- production Site URL matches the deployed frontend origin
- production `/chat` redirect is explicitly allowed
- Google and GitHub callback URLs reference the production Supabase project
- backend `FRONTEND_URL` and frontend `VITE_API_URL` use HTTPS
- no localhost, `127.0.0.1`, staging, preview, or wildcard origin is present in
  production CORS

Dashboard changes should be performed and reviewed separately from this code
change.
