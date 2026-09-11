# Decisions

## Decision 1 — Deploy early, then reversed to build first

- **Chose:** originally, a deployment walking skeleton as phase 2: one row
  travelling from Postgres through the API to the browser on live URLs, before
  any business logic existed.
- **Rejected:** building the application locally and deploying at the end.
- **Why:** deployment is the highest-risk step and the one most likely to
  produce a nasty surprise. Discovering a broken pipeline at hour 11, with the
  app already written, is how this kind of project fails. Doing it first means
  every later phase ships to a live URL.
- **Later reversed:** I reversed this partway through. Standing up three cloud
  accounts before there was anything to show felt like the wrong use of a
  12-hour budget, and I would rather spend the early hours on the business rules
  that are actually assessed. What I kept from the original position: the API
  takes every setting from environment variables and fails at startup if one is
  missing, `render.yaml` is committed, and the frontend reads its base URL from
  `NEXT_PUBLIC_API_BASE_URL` and never hard-codes a host. So deployment should
  be a configuration job rather than a rewrite. I am aware that is exactly what
  everyone says before a deployment goes badly, and the risk is mine.
- **Trade-off:** if the deployment does go badly, it goes badly late, which is
  the situation the original plan existed to avoid.

## Decision 2 — Overdue is derived, and only dismissals are stored

- **Chose:** a table called `overdue_alert_dismissals` holding one row per
  dismissed alert. Whether a service is overdue is computed:
  `status = 'due'` and `due_since + grace period <= now()`.
- **Rejected:** an `overdue_alerts` table with a row per alert and a
  `dismissed_at` column.
- **Why:** stored alert rows have to be created by something, either a scheduled
  job or a write during a read. Then there are two answers to "is this vehicle
  overdue", and they can disagree. Deriving it means the current state always
  follows from the data and the clock. The reappearance rule falls out for free:
  one service record is one service cycle, so the next cycle is a different row
  with no dismissal against it, and the alert comes back without any special
  handling.
- **Trade-off:** it deviates from the `OverdueAlert` entity in the original
  design notes, and there is no stored record of when an alert first appeared,
  only of when it was dismissed. If alert history were ever needed, it would
  have to be reconstructed from the audit trail.

## Decision 3 — The audit table is immutable in the database, not just in the API

- **Chose:** `BEFORE UPDATE` and `BEFORE DELETE` row triggers on `audit_events`
  that raise an exception.
- **Rejected:** simply not writing update or delete endpoints, which is the
  usual way this requirement gets met.
- **Why:** the requirement is that nothing in the timeline can be changed after
  the fact, including by fleet managers. Not writing an endpoint is a promise
  about today's code. A trigger is a property of the data, and it holds for the
  ORM, for a future script, and for anyone with a psql prompt. It cost about ten
  lines of migration.
- **Trade-off:** the test suite cannot clean up with `DELETE`, so it uses
  `TRUNCATE`, which row triggers do not fire on. That is a small oddity to
  explain to anyone reading the test setup. If an audit row is ever written
  wrong, correcting it needs a migration.

## Decision 4 — `due_since` is stored rather than recomputed

- **Chose:** persist the moment a service cycle became due, on the service
  record.
- **Rejected:** deriving it from the last completed service date and the
  vehicle's interval whenever it is needed.
- **Why:** the overdue grace period counts from when the record became due. If
  that instant is recomputed from the vehicle's current intervals, then editing
  a vehicle's service interval silently moves an overdue clock that is already
  running, and a vehicle that was overdue yesterday quietly stops being overdue
  today. Storing the event removes that whole class of bug.
- **Trade-off:** one more column to keep correct, and it has to be set at
  exactly the right moment in the lifecycle rather than being self-healing.

## Decision 5 — Status values are VARCHAR with a check constraint

- **Chose:** `varchar(20)` columns with `CHECK (status IN (...))`, and Python
  `StrEnum` types beside them for the application.
- **Rejected:** native PostgreSQL enum types.
- **Why:** adding a value to a native enum means `ALTER TYPE` and the migration
  awkwardness that comes with it. A check constraint is dropped and recreated in
  one line. The values also stay readable in a psql session without a join or a
  cast. There are exactly four lifecycle statuses and adding a fifth is
  explicitly something I want to make harder, not easier, but the same schema
  holds `event_type` on the audit table, which I do expect to grow.
- **Trade-off:** less type safety at the database level than a real enum, and
  the valid values are written in two places, the migration and the Python enum.
  A test asserts they cannot drift on the one that matters most: storing
  `'overdue'` as a status fails.

## Decision 6 — The health check touches the database

- **Chose:** `GET /health` runs `SELECT 1` and returns 503 with
  `{"status": "degraded", "database": "unreachable"}` when it fails. Render's
  health check points at it.
- **Rejected:** a health check that returns 200 as long as the process is up.
- **Why:** a liveness check that never touches its dependencies is how a service
  with a broken `DATABASE_URL` sits in production looking healthy.
- **Trade-off:** a database blip can now take the service out of rotation and
  trigger a restart, where it would otherwise have stayed up serving errors.
  That is the bargain I wanted, but it is a bargain.
- **Found while testing it:** running the API against an unroutable database
  host showed that psycopg waits indefinitely rather than failing, so `/health`
  hung instead of answering 503, which is the one thing it exists to do. A five
  second connect timeout fixed it. The health check had been quietly useless in
  the exact case it was written for.

## Decision 7 — No odometer history table

- **Chose:** `vehicles.current_odometer` is the single source of truth for
  odometer validation.
- **Rejected:** an `odometer_readings` table recording every reading received.
- **Why:** the rule is that a reading lower than the vehicle's most recent one
  is rejected, and `current_odometer` answers that directly. The odometer needed
  for service cycle maths is the completion odometer, already stored on the
  completed service record. A history table would add a migration, a repository
  and a join to satisfy nothing that was asked for.
- **Trade-off:** no per-reading audit trail. A wrong but higher reading is
  accepted and cannot be traced back to the CSV row that introduced it. If that
  ever matters, the fix is to introduce the table and make it the source of
  truth consistently, not to keep both.

## Decision 8 — The test database is local PostgreSQL, after starting somewhere else

- **Chose:** a local PostgreSQL 17 cluster with a separate `fleet_maintenance_test`
  database, pointed at by `TEST_DATABASE_URL`.
- **Rejected:** a second free Supabase project as the test database, and reusing
  the single application database for tests.
- **Why:** reusing one database is unsafe, because the migration round-trip test
  runs `alembic downgrade base` and would drop the real tables. Between the
  other two, local wins on speed: the constraint tests are the ones run on every
  change, and seconds of network latency per test is how a suite stops being
  run.
- **Later reversed:** I picked the second Supabase project first, on the grounds
  that it matches production exactly and needs no install. I changed my mind
  once the tests became the main feedback loop rather than an occasional check.
- **Trade-off:** local PostgreSQL 17 is not byte-identical to Supabase, so
  something could pass locally and fail there. The migration still has to be run
  against the real database before the deployment is trusted, and that is on the
  deployment checklist rather than left to chance.
