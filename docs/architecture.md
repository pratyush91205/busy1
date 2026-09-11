# Architecture

## The pieces

- **apps/web** — Next.js 16 App Router, TypeScript, Tailwind, TanStack Query.
  No business rules; renders loading, error, empty and success for every answer.
- **apps/api** — FastAPI, Python 3.13, SQLAlchemy 2, Alembic. All rules live
  here, layered route → service → repository → database.
- **PostgreSQL 17** — data, plus constraints and the triggers that keep
  `audit_events` append-only.

JSON over HTTPS between browser and API, a connection pool between API and
database. No queue, cache or worker: maintenance state is computed from the data
and the clock, so nothing needs keeping warm.

## Where each runs

Locally for now — a local Postgres cluster, uvicorn, `next dev`. Production is
meant to be Supabase, Render and Vercel; `render.yaml` is committed, all config
is environment-driven, no hard-coded hosts. Not deployed yet (see
`decisions.md`).

## Request path: completing a service

`POST /services/{id}/complete` with a bearer token →
`get_db` opens a session and `require_role("fleet_manager")` decodes the token
and re-reads the user from the database, so a tampered role claim gets 403 →
the route calls one service-layer function → in one transaction: reject any
current status other than `in_service` with 409, write `completed_at` and
`completion_odometer`, append a `status_changed` audit event with old, new and
actor, close out the cycle's overdue state → commit, or roll all of it back.

The rollback is the point: a service can't be completed with no audit event to
show for it.

## Authentication

`POST /auth/login` checks a bcrypt hash and returns a 12-hour HS256 token
carrying `sub`, `role` and `exp`. A wrong password and an unknown email give the
same 401 and the same message, and the unknown-email path spends a dummy bcrypt
verification so the two take comparable time — otherwise the pair answers "does
this address have an account" for anyone with a stopwatch.

Protected routes depend on `get_current_user`, which decodes the token and then
loads the user from the database. The `role` claim is never consulted for a
decision, so rewriting it gains nothing (`decisions.md`, 10).
`require_role("fleet_manager")` is the only authorization primitive; it can't
express "only the records assigned to me", which is per-resource and belongs to
the service layer that owns the resource.

The browser keeps the token in `localStorage` and reads the user from
`/auth/me`, never by decoding the token. The `(app)` layout's redirect is
convenience — bypassing it gets a screen of 401s.

Built so far: `GET /health`, which runs `SELECT 1` and returns 503 if the
database doesn't answer, plus `POST /auth/login` and `GET /auth/me`.

## Not built

- Refresh tokens — 12-hour access token, then log in again.
- A signup endpoint — users are seeded; one accepting a role would undermine
  the authorization model.
- Login rate limiting — needs shared state, which a free tier doesn't have.
- Odometer history and stored overdue alerts — see `decisions.md`.
- Any scheduler. Maintenance state must follow from the database and the clock.
