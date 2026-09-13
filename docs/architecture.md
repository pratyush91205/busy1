# Architecture

## The pieces

- **apps/web** — Next.js 16 App Router, TypeScript, Tailwind, TanStack Query.
  No business rules; renders loading, error, empty and success for every answer.
  Two shells, one per role (`decisions.md`, 27).
- **apps/api** — FastAPI, Python 3.13, SQLAlchemy 2, Alembic. All rules live
  here, layered route → service → repository → database.
- **PostgreSQL 17** — data, plus constraints and the triggers that keep
  `audit_events` append-only.

JSON over HTTPS between browser and API, a connection pool between API and
database. No queue, cache or worker: maintenance state is computed from the data
and the clock, so nothing needs keeping warm.

## Where each runs

Locally for now — uvicorn and the production build (`next build`, then
`next start`) against a Supabase project in ap-south-1 (Mumbai). `next dev`
compiles each page on request, which on this machine meant seconds per page, so
it is for editing only; the build bakes in the API address, so it is rebuilt
when that changes. pytest runs against a local Postgres cluster instead,
because the suite migrates its database up and down. Production is meant to be
Render and Vercel; `render.yaml` pins Render to Singapore, the nearest region
to the database, since every query is a round trip between the two and a
request makes several (`decisions.md`, 31). All config is environment-driven,
no hard-coded hosts. Not deployed yet.

## Request path: completing a service

`POST /services/{id}/complete` with a bearer token →
`get_db` opens a session and `require_role("fleet_manager")` decodes the token
and re-reads the user from the database, so a tampered role claim gets 403 →
the route calls one service-layer function → in one transaction: reject any
current status other than `in_service` with 409, write `completed_at` and
`completion_odometer`, append a `status_changed` audit event with old, new and
actor, close out the cycle's overdue state → commit, or roll all of it back.

The rollback is the point: a service can't be completed with no audit event to
show for it. `audit_repository.record` adds to the session and never commits,
so that property belongs to the API rather than to each caller remembering.
A test installs a trigger that makes the audit insert fail and asserts the
status change goes with it.

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
database doesn't answer; `POST /auth/login` and `GET /auth/me`; the six
vehicle routes; ten service routes; `GET /technicians`; three alert routes;
the odometer upload; the CSV export; and `GET /dashboard`.

## The dashboard

One endpoint, six aggregate queries, all counted by PostgreSQL. It imports
the due and overdue predicates rather than rewriting them, and a test
asserts the overdue tile equals the alert badge — two queries over one idea
will otherwise drift, and a manager can't tell which is lying.

Weeks are ISO-8601 in UTC. `date_trunc('week')` is already ISO in
PostgreSQL, so the bucketing is one SQL expression rather than Python date
arithmetic. The service layer fills in the gaps the database can't return:
a status with no records, a week with no completions, a technician with
nothing assigned. Each has to be a zero rather than absent.

"Due for service" counts vehicles whose cycle is Due and unbooked, not every
vehicle past its interval. A booked or in-service vehicle has passed its
interval too, and counting it would put one vehicle in two tiles.

## CSV in and out

The bulk odometer upload is the one place that isn't one transaction per
request. Each row commits alone, so a single typo can't discard the rest of
a depot's readings. The only whole-file rejection is a bad header — that
isn't a wrong row, it means the file isn't what the endpoint takes. Rules
aren't reimplemented for CSV: it calls the same `vehicle_service` checks the
API uses, so the two can't disagree.

The export streams row by row from a cursor, filtered by the same
parameters as the service list. Nothing is assembled in the browser.

## Due and overdue: two questions

Easy to conflate, kept apart deliberately.

**Is a vehicle due?** From its intervals and the point the current cycle
counts from. Either interval alone is enough — they are not required
together. It's what opens the vehicle's next cycle.

**Is a record overdue?** From status `due`, `due_since`, and the grace
period. It's about a record that was opened and then left unbooked.

A vehicle that falls due opens its own Due record. Mileage only moves when an
odometer reading is written, so the write that crosses the interval opens the
cycle in the same transaction. The date moves with the clock and nothing writes
when it passes, so alerts, the dashboard, the lists and the export open due
cycles before they read — idempotently, with `due_since` set to the day the
interval landed rather than the moment someone looked. A manager can still open
a record early, so a record can be overdue for a vehicle not otherwise due.
Still no job: what gets opened follows from the database and the clock, not
from when the sweep ran (`decisions.md`, 33).

An alert is not a row either. It *is* an overdue record, so there's nothing
to create or reconcile and nothing that can disagree with the records. Only
the dismissal is stored, and because it points at a record and one record
is one cycle, the next cycle's alert appears with nothing to reset. The
dismissal row is its own audit trail — who and when — so it isn't in
`audit_events`, whose five types are a closed set with a check constraint.

## Two kinds of authorization

`require_role("fleet_manager")` is a route dependency and answers "what is
this user". It cannot answer "is this record theirs", which is per-resource
and lives in the service layer: a technician sees only records they are
assigned to, and one they aren't gets 404 rather than 403.

Some rules need both. An assigned technician may start and complete a
service — that is the work — but booking sets the schedule and who does
the work, and stays a manager's. So the transition endpoint has no role dependency at all; the
check depends on which move is being asked for.

## Listing

`GET /vehicles` filters, sorts and pages in SQL — `ILIKE`, `ORDER BY`,
`LIMIT`, `OFFSET`, one `COUNT`. `limit` is capped at 100 so a list endpoint
can't become a full-table export, sort columns are an enum rather than an
interpolated string, and `%` in a search term is escaped. The shape
(`items`, `total`, `page`, `limit`, `total_pages`) is shared, so the service
listing reuses it rather than inventing a second one.

Sorting services by status sorts by lifecycle position — Due, Booked, In
Service, Completed — through a `CASE`. The stored strings sort alphabetically,
which puts Booked first and Due third.

## What the browser does

Nothing that decides anything. Two shells — a manager console, a technician
queue — chosen from the role the server reports, so a technician who types
`/alerts` is redirected *and* refused (`decisions.md`, 27).

Every list keeps its filters, sort, page and page size in the URL, which is
what makes a filtered view shareable and what keeps filtering on the server
where it belongs: the parameter goes to the API or nothing happens. Search
waits 300ms after typing stops, so a ten-character registration is one request
rather than ten. TanStack Query holds the previous page on screen while the
next one loads, and invalidates by key after a mutation — completing a service
re-reads the vehicle, because the vehicle's odometer moved.

Five colours mean something (Due, Overdue, Booked, In Service, Completed), and
they come from tokens rather than per-component classes, so a status looks the
same in a badge, a row edge and the lifecycle rail. Every badge carries its
text: colour alone isn't a label.

## Not built

- Refresh tokens — 12-hour access token, then log in again.
- A signup endpoint — users are seeded; one accepting a role would undermine
  the authorization model.
- Login rate limiting — needs shared state, which a free tier doesn't have.
- Any audit trail for vehicles. `audit_events.service_id` is NOT NULL, so
  the table can't hold a vehicle-scoped event: who archived a vehicle or
  changed an interval is logged, not recoverable from the database. Doing it
  properly means making `service_id` nullable and adding an entity column.
- A DELETE for vehicles. Archive is the only removal, which is what keeps
  service history readable.
- Odometer history and stored overdue alerts — see `decisions.md`.
- Any scheduler. Maintenance state must follow from the database and the clock.
- A frontend test runner. Playwright was the optional goal and the budget went
  elsewhere; the frontend is covered by type-check, lint, a production build
  and by hand.
