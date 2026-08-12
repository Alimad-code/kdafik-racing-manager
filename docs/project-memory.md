# Kdafik Racing Manager Project Memory

Last updated: 2026-08-10

## What This Project Is

- Single-player Formula-style season manager with a React/Vite frontend and FastAPI backend.
- Runtime data is supplied by the backend through the `SeasonRepository` boundary.

## Current Implementation State

- User-facing runtime modes are `local` and `production`; `test` is an internal backend profile.
- One root `compose.yaml` is the only user-facing launch. Its `local` profile runs PostgreSQL on the usual Compose-managed named volume (`kdafik-racing-manager_local_postgres_data`); production uses an external PostgreSQL URL. Existing local seasons were safely migrated to this volume and verified.
- Services are `db` (local only), one-shot `migrate`, `backend` and `web`. A successful `migrate` exits and consumes no runtime memory.
- Runtime settings fail closed in production for debug, database URL, JWT secret, refresh-cookie security, CORS origins and trusted hosts.
- The frontend no longer has a global environment indicator or build-time environment branch.
- Registration creates a hash-token-protected pending record; explicit confirmation creates the verified account and first season without issuing a session.
- Public legal pages are served from checked `docs/legal` sources and rendered as semantic Markdown.

## Legal Status

- The legal sources and manifest are still DRAFT document material and require Russian legal review before publication.
- Local runtime may serve the verified draft documents. Production validation intentionally blocks DRAFT text, unresolved placeholders, missing sources and stale hashes.

## Architecture Notes

- Frontend route pages use the repository/store boundary rather than direct API requests.
- Backend images include `backend/legal_manifest.json` and the legal sources; migration bootstrap applies Alembic, imports legal metadata and seeds the canonical MVP catalog.

## Next Priority

- Finalize the legal set with a Russian lawyer before enabling production.
