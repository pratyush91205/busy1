# Decisions

## Decision 1

- **Chose:** a deployed walking skeleton before any business logic.
- **Rejected:** building locally and deploying at the end.
- **Why:** deployment is the riskiest step, and finding it broken at hour 11
  with the app already written is how this fails.
- **Later reversed:** three cloud accounts before there was anything to show was
  the wrong use of the budget. Kept from it: all config is environment-driven
  and the API won't start without it, `render.yaml` is committed, the frontend
  reads `NEXT_PUBLIC_API_BASE_URL`. Trade-off: if deployment goes wrong now, it
  goes wrong late.

## Decision 2

- **Chose:** overdue is derived (`status = 'due'` and `due_since + grace <=
  now()`); only dismissals are stored.
- **Rejected:** an `overdue_alerts` table with a row per alert.
- **Why:** stored alerts need a job or a write-on-read to create them, and then
  two answers to "is this overdue" that can disagree. Deriving it also makes
  reappearance automatic — a new cycle is a new record with no dismissal on it.
  Trade-off: no record of when an alert first appeared.

## Decision 3

- **Chose:** BEFORE UPDATE and BEFORE DELETE triggers on `audit_events`.
- **Rejected:** simply not writing update or delete endpoints.
- **Why:** no endpoint is a promise about today's code; a trigger is a property
  of the data and holds through the ORM or a psql prompt. Trade-off: tests clean
  up with TRUNCATE, and fixing a bad audit row would need a migration.

## Decision 4

- **Chose:** store `due_since` on the service record.
- **Rejected:** recomputing it from the last completed service and the interval.
- **Why:** the grace period counts from that moment. Recomputed, editing a
  vehicle's interval silently moves an overdue clock that's already running.

## Decision 5

- **Chose:** status and event_type as varchar + check constraint.
- **Rejected:** native PostgreSQL enum types.
- **Why:** adding a value is a one-line migration instead of `ALTER TYPE`, and
  values stay readable in psql. Trade-off: the valid set is written twice, so a
  test asserts the important half — storing `'overdue'` as a status fails.

## Decision 6

- **Chose:** `/health` runs `SELECT 1` and returns 503 when it fails.
- **Rejected:** returning 200 whenever the process is up.
- **Why:** a check that never touches its dependencies is how a service with a
  broken `DATABASE_URL` looks healthy in production. Testing it against an
  unroutable host then showed psycopg waiting forever rather than failing, so
  the check hung instead of answering — fixed with a 5s connect timeout.

## Decision 7

- **Chose:** local PostgreSQL 17 for the test database.
- **Rejected:** a second Supabase project; reusing the one app database.
- **Why:** reusing one database is unsafe, since the round-trip test runs
  `downgrade base`. Local wins on speed, and a slow suite stops being run.
- **Later reversed:** I picked the Supabase project first, for matching
  production with nothing to install, and changed my mind once the tests became
  the main feedback loop. Trade-off: the migration still has to be run against
  the real database before the deployment is trusted.
