# Architecture

## The moving pieces

Three of them, kept deliberately boring.

**`apps/web`** is a Next.js 16 app using the App Router, TypeScript, Tailwind 4
and TanStack Query for server state. It holds no business rules. It knows how to
ask the API questions and how to render the four states of any answer: loading,
error, empty, and success.

**`apps/api`** is a FastAPI service on Python 3.13 with SQLAlchemy 2 and Alembic.
This is where the rules live. It is layered as route, then service, then
repository, then database, and route handlers stay thin enough to read in one
go.

**PostgreSQL 17** holds the data and a fair amount of the correctness: unique
constraints, check constraints, foreign keys, and triggers that make the audit
table append-only.

The browser talks to the API over HTTPS with JSON. The API talks to PostgreSQL
over a connection pool. There is no message queue, no cache and no background
worker, and the design tries to keep it that way: the maintenance state of a
vehicle is computed from data plus the current time, so nothing has to be kept
warm by a job.

## Where each piece runs

Right now, all of it runs locally. PostgreSQL 17 runs as a local cluster, the
API under uvicorn, the frontend under `next dev`.

The intended production layout is Supabase for the database, Render for the API
and Vercel for the frontend, and the repository is already shaped for it:
`render.yaml` is committed, every setting comes from environment variables, and
no host is hard-coded anywhere in the frontend. Deployment has not happened yet.
That is a deliberate ordering choice, and the risk it carries is written up in
`decisions.md`.

## One request, end to end

Take a fleet manager completing a service. The path will be:

1. The browser sends `POST /services/{id}/complete` with a bearer token.
2. FastAPI resolves the route's dependencies. `get_db` opens a session for this
   request; `require_role("fleet_manager")` decodes the token, re-reads the user
   from the database, and returns 403 if the role is wrong. The role in the
   token is not trusted for the decision, so a role change takes effect on the
   next request rather than the next login.
3. The route calls one service-layer function and does nothing else itself.
4. The service layer opens a transaction and, inside it: validates that the
   current status is `in_service`, rejecting anything else with 409 and a
   message naming both states; writes `completed_at` and
   `completion_odometer`; appends a `status_changed` audit event with the old
   and new values and the actor; and closes out the cycle's overdue state.
5. Commit. If any step raises, the whole thing rolls back, which is what stops a
   service being marked complete with no audit event to show for it.
6. The response goes back as JSON. TanStack Query invalidates the affected
   queries and the page re-renders.

Today the only endpoint that actually exists is `GET /health`, which runs
`SELECT 1` and returns 503 if the database does not answer. That is on purpose:
a health check that only proves the web process is alive is what lets a broken
`DATABASE_URL` sit in production looking green.

## What I decided not to build

- **A refresh token.** Access tokens last 12 hours and that is the whole session
  story. Refresh flows are real work and no assessed goal asks for one.
- **A signup endpoint.** Users are seeded. An open registration endpoint that
  accepted a role would undermine the authorization model that the rest of the
  system rests on.
- **Login rate limiting.** It needs shared state to be worth anything, and there
  is none on a free tier. Worth naming rather than leaving a reviewer to wonder
  whether I forgot.
- **An odometer history table.** Reasoning and its cost are in `schema.md`.
- **Stored overdue alerts and the job that would create them.** Overdue is
  derived. Only dismissals are stored.
- **A background scheduler of any kind.** Maintenance state has to be derivable
  from the database and the clock. A job can improve notifications later without
  becoming the source of truth.
- **Server-side rendering of authenticated data.** The token lives in
  `localStorage` and is sent as a bearer header, so pages fetch on the client.
  It trades a little first-paint latency for not having to run cross-site
  cookies between two different origins.
