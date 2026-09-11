# Decisions

## 1. Deploy early — reversed to build first

- **Chose:** originally, a deployed walking skeleton before any business logic.
- **Rejected:** building locally and deploying at the end.
- **Why:** deployment is the highest-risk step. Finding it broken at hour 11,
  with the app written, is how this kind of project fails.
- **Later reversed:** standing up three cloud accounts before there was anything
  to show was the wrong use of a 12-hour budget. What I kept: all config comes
  from environment variables and the API refuses to start without them,
  `render.yaml` is committed, and the frontend reads its base URL from
  `NEXT_PUBLIC_API_BASE_URL`. So deployment should be configuration, not a
  rewrite.
- **Trade-off:** if it does go wrong, it now goes wrong late — exactly what the
  original plan existed to prevent.

## 2. Overdue is derived; only dismissals are stored

- **Chose:** `overdue_alert_dismissals`, one row per dismissed alert. Overdue
  itself is computed: `status = 'due'` and `due_since + grace <= now()`.
- **Rejected:** an `overdue_alerts` table with a row per alert.
- **Why:** stored alerts need something to create them, a job or a write during
  a read, and then two answers to "is this overdue" that can disagree. Deriving
  it also gives the reappearance rule for free: a new cycle is a new record with
  no dismissal against it, so the alert returns with no special handling.
- **Trade-off:** no record of when an alert first appeared, only when it was
  dismissed.

## 3. Audit immutability enforced by the database

- **Chose:** `BEFORE UPDATE` and `BEFORE DELETE` triggers on `audit_events`
  that raise.
- **Rejected:** just not writing update or delete endpoints.
- **Why:** not writing an endpoint is a promise about today's code. A trigger is
  a property of the data and holds for the ORM, a future script, or anyone with
  a psql prompt. Ten lines of migration.
- **Trade-off:** tests clean up with `TRUNCATE` instead of `DELETE`. Fixing a
  bad audit row would need a migration.

## 4. `due_since` is stored, not recomputed

- **Chose:** persist the moment a cycle became due.
- **Rejected:** deriving it from the last completed service and the interval.
- **Why:** the grace period counts from that moment. Recomputed, editing a
  vehicle's interval silently moves an overdue clock that's already running, and
  a vehicle overdue yesterday quietly isn't today.
- **Trade-off:** one more column that has to be set at the right point in the
  lifecycle rather than healing itself.

## 5. Status values as varchar + check, not a native enum

- **Chose:** `varchar(20)` with a check constraint, plus `StrEnum` in Python.
- **Rejected:** PostgreSQL enum types.
- **Why:** adding a value means dropping and recreating a constraint rather than
  `ALTER TYPE`, and values stay readable in psql. Matters more for
  `audit_events.event_type`, which I expect to grow, than for status, which I
  want to be hard to extend.
- **Trade-off:** values written in two places, the migration and the enum. A
  test covers the one that matters: storing `'overdue'` as a status fails.

## 6. The health check touches the database

- **Chose:** `/health` runs `SELECT 1`, returns 503 when it fails, and is
  Render's health check path.
- **Rejected:** returning 200 whenever the process is up.
- **Why:** a check that never touches its dependencies is how a service with a
  broken `DATABASE_URL` sits in production looking healthy.
- **Trade-off:** a database blip can now take the service out of rotation.
- **Found by testing it:** against an unroutable host, psycopg waited forever
  instead of failing, so `/health` hung rather than answering 503 — the one
  thing it exists to do. A five second connect timeout fixed it. The code had
  looked right and the unit test passed, because that test used a session that
  raises immediately.

## 7. The test database is local Postgres

- **Chose:** a local PostgreSQL 17 cluster with a separate
  `fleet_maintenance_test` database.
- **Rejected:** a second Supabase project, and reusing the one application
  database.
- **Why:** reusing one database is unsafe — the migration round-trip test runs
  `downgrade base` and would drop the real tables. Between the other two, local
  wins on speed, and a suite that takes seconds per test stops being run.
- **Later reversed:** I picked the second Supabase project first, for matching
  production exactly with nothing to install. I changed my mind once the tests
  became the main feedback loop.
- **Trade-off:** local Postgres isn't byte-identical to Supabase, so the
  migration still has to be run against the real database before the deployment
  is trusted.
