# Architecture

## The pieces

**`apps/web`** — Next.js 16 (App Router), TypeScript, Tailwind, TanStack Query.
No business rules. It asks the API questions and renders four states for every
answer: loading, error, empty, success.

**`apps/api`** — FastAPI on Python 3.13, SQLAlchemy 2, Alembic. All the rules
live here, layered route → service → repository → database.

**PostgreSQL 17** — the data, plus a share of the correctness: unique and check
constraints, foreign keys, and triggers making the audit table append-only.

Browser to API is JSON over HTTPS. API to database is a connection pool. No
queue, no cache, no background worker, and I'd like to keep it that way:
maintenance state is computed from the data and the current time, so nothing has
to be kept warm by a job.

## Where it runs

Locally, for now — Postgres as a local cluster, the API under uvicorn, the
frontend under `next dev`.

The intended production layout is Supabase, Render and Vercel. `render.yaml` is
committed, every setting comes from environment variables, and no host is
hard-coded in the frontend. Deployment hasn't happened yet; the reasoning and
the risk are in `decisions.md`.

## One request: completing a service

1. Browser sends `POST /services/{id}/complete` with a bearer token.
2. Dependencies resolve: `get_db` opens a session, `require_role("fleet_manager")`
   decodes the token and re-reads the user from the database. The role claim in
   the token isn't trusted for the decision, so a role change takes effect on
   the next request rather than the next login. Wrong role is 403.
3. The route calls one service-layer function and does nothing else.
4. In one transaction: check the current status is `in_service` (anything else
   is 409, naming both states), write `completed_at` and `completion_odometer`,
   append a `status_changed` audit event with old value, new value and actor,
   and close out the cycle's overdue state.
5. Commit, or roll all of it back. That's what stops a service being completed
   with no audit event to show for it.

Today the only endpoint that exists is `GET /health`, which runs `SELECT 1` and
returns 503 if the database doesn't answer.

## Not built, on purpose

- **Refresh tokens.** 12-hour access token, then log in again.
- **A signup endpoint.** Users are seeded. An endpoint that accepted a role
  would undermine the authorization model.
- **Login rate limiting.** Needs shared state to be worth anything, and there
  isn't any on a free tier.
- **An odometer history table** and **stored overdue alerts** — see
  `decisions.md`.
- **Any background scheduler.** Maintenance state must be derivable from the
  database and the clock.
