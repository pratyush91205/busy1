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

## Decision 8

- **Chose:** access token in `localStorage`, sent as a bearer header.
- **Rejected:** an httpOnly cookie.
- **Why:** the API and the frontend are on different origins, so a cookie needs
  `SameSite=None; Secure` plus credentialed CORS on both ends. That's more
  moving parts to get wrong than the XSS exposure it removes, on an app that
  renders no user-supplied HTML. Trade-off: a successful XSS reads the token,
  and the 12-hour expiry is the only thing bounding that.

## Decision 9

- **Chose:** no signup endpoint. Users come from `scripts/create_user.py`.
- **Rejected:** a registration route, even one restricted to managers.
- **Why:** the goals need sign-in, not user management, and a route that
  accepts a role is exactly the hole the rest of the system spends its time
  closing. With no such route, "a client cannot choose its own role" is a
  property of the API surface rather than a validation that has to hold.
  Trade-off: demo accounts have to be seeded, so their credentials belong in
  `SUBMISSION.md`.

## Decision 10

- **Chose:** re-read the user row on every authenticated request; the `role`
  claim in the token is for logging and for deciding which buttons to draw.
- **Rejected:** trusting the claim, which is signed and therefore not forgeable.
- **Why:** signed is not the same as current. Trusting it means a role changed
  in the database does nothing until the token expires, up to 12 hours later,
  and a deleted user keeps working. It also leaves one decision resting on the
  key never leaking. A test signs a token claiming `fleet_manager` for a
  technician with the application's own key and asserts 403. Trade-off: one
  indexed primary-key lookup per request.

## Decision 11

- **Chose:** normalise registration numbers to trimmed uppercase before every
  write and lookup.
- **Rejected:** a case-insensitive unique index, or storing whatever was typed.
- **Why:** the unique index is case-sensitive, so `van001` and `VAN001` would be
  two vehicles for the same van. Normalising makes the index already there
  sufficient, and uppercase is the form on the plate. Trade-off: a registration
  that is genuinely lowercase can't be stored as typed, which UK plates never
  are.

## Decision 12

- **Chose:** an archived vehicle refuses every edit until it is restored.
- **Rejected:** letting archived vehicles be edited normally.
- **Why:** the brief doesn't require this, but it gives the bulk-odometer
  upload a real answer for a row naming an archived vehicle — rejected, with a
  reason — instead of quietly updating something nobody is driving. Trade-off:
  fixing a typo on an archived vehicle takes two calls.

## Decision 13

- **Chose:** service functions raise domain errors; one handler maps them to
  status codes.
- **Rejected:** raising `HTTPException` from the service layer.
- **Why:** a business rule isn't an HTTP concern, and a rule that raises
  `HTTPException` can't be tested without a request. Routes end up with no
  try/except and the shape of a 409 is decided once. Trade-off: one more
  indirection between raising and the response.
