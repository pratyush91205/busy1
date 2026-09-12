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

## Decision 14

- **Chose:** a vehicle may have at most one open service record.
- **Rejected:** any number of concurrent open cycles.
- **Why:** "the current service cycle" has to mean something for due and
  overdue to be computable at all, and one record is one cycle. It also makes
  alert dismissal cycle-scoped for free. Trade-off: a fleet that services a
  vehicle twice at once can't be modelled — not something a logistics fleet
  does, but it is an invented constraint and worth owning.

## Decision 15

- **Chose:** one `POST /services/{id}/transition` taking the target status.
- **Rejected:** `/book`, `/start`, `/complete`.
- **Why:** the transition table stays in one function instead of being spread
  across three handlers, and adding a status later adds no route. Trade-off:
  the body carries `scheduled_date` and `completion_odometer`, each required by
  exactly one target, which is validated per target rather than by the schema.

## Decision 16

- **Chose:** a technician reading a record they aren't assigned to gets 404.
- **Rejected:** 403, which is the literal truth.
- **Why:** 403 confirms the id exists, so walking the ids maps the whole fleet.
  404 says nothing. Trade-off: a technician who really was assigned a second
  ago sees a confusing "no such record" rather than "not yours".

## Decision 17

- **Chose:** the description endpoint takes a description and nothing else,
  and rejects any other field outright.
- **Rejected:** accepting a wider body and ignoring the fields not allowed.
- **Why:** an assigned technician may edit a description. If that schema also
  carried `status` or `technician_ids`, that permission would quietly become
  the permission to reassign the record or skip the lifecycle. Ignoring extra
  fields relies on remembering to; not accepting them is structural.

## Decision 18

- **Chose:** store `service_baseline_odometer` and `service_baseline_date` on
  the vehicle, reset on each completion.
- **Rejected:** deriving both from the newest completed service record.
- **Why:** `current_odometer` can't be its own baseline — it moves, so "due at
  current + interval" is a target that runs away as the van is driven. Zero is
  worse: a used van joining with 80,000 miles would be due the day it arrived.
  The date half could have been derived, but that's a lateral join on every row
  of a filtered fleet list, and keeping the two halves symmetric makes due-ness
  a single-table predicate. Trade-off: two columns that have to be kept
  correct on completion, rather than one place to read the truth from.

## Decision 19

- **Chose:** the due and overdue rules take `now` and the grace period as
  arguments.
- **Rejected:** reading `datetime.now()` and the setting inside them.
- **Why:** a record can then be aged two weeks in a test without sleeping or
  patching the clock, and two apps with different grace periods can disagree
  about the same row — which is how I know the grace period is really
  configuration and not a hard-coded 7. Trade-off: every caller has to pass
  them, so `utc_now()` exists to keep that honest in one place.

## Decision 20

- **Chose:** the due filter in SQL and the per-row answer in Python, with a
  test asserting they agree.
- **Rejected:** one implementation used for both.
- **Why:** paging and totals have to be filtered in the database, and the
  detail view needs the reason, not just a boolean. Two implementations of one
  rule will drift, so the test compares the full unfiltered list's computed
  answers against the filtered set. Trade-off: the rule is written twice.

## Decision 21

- **Chose:** no transaction around a bulk odometer upload. Each row commits on
  its own.
- **Rejected:** one transaction for the file, which is what every other write
  in this codebase does.
- **Why:** a depot uploads fifty readings and one is a typo. Rolling back the
  other forty-nine makes the feature useless, and the brief asks for per-row
  results explicitly. Trade-off: a crash mid-file leaves a partial run. That's
  acceptable because every row that landed was individually valid, and
  re-uploading is safe — a repeated reading is an accepted no-op.

## Decision 22

- **Chose:** the CSV identifies vehicles by registration number.
- **Rejected:** the database id.
- **Why:** the person uploading readings from the depot knows the plate, not a
  surrogate key. It also means the normaliser has to be shared with the API, or
  a registration that works in the form is unknown in the file — so
  `normalise_registration` is one function used by both.

## Decision 23

- **Chose:** the export streams row by row from a server-side cursor.
- **Rejected:** building the CSV as one string and returning it.
- **Why:** at fleet scale either works, but this costs nothing to write now and
  stops the export being the first endpoint to fall over as data grows. The
  brief also calls out building reports in the browser as the thing not to do,
  and streaming makes that impossible rather than merely avoided.

## Decision 24

- **Chose:** one `/dashboard` endpoint returning the whole summary.
- **Rejected:** one endpoint per figure.
- **Why:** the dashboard is one screen. Six round trips is six chances for a
  half-drawn answer, and the queries are all indexed counts. Trade-off: no
  partial refresh — the whole summary reloads or none of it does.

## Decision 25

- **Chose:** the dashboard imports the due and overdue predicates rather than
  rewriting them, and a test asserts the overdue tile equals the alert badge.
- **Rejected:** writing the aggregate queries independently.
- **Why:** two queries over one idea will drift, and when the tile and the
  badge disagree a manager has no way to tell which is lying. Asserting they're
  *equal* catches that; asserting each is correct separately would not.

## Decision 26

- **Chose:** the seed script drives the service layer.
- **Rejected:** inserting demo rows with SQL.
- **Why:** the demo data then obeys every rule the app does, and cycle numbers,
  baselines and audit timelines come out right without being reproduced by
  hand. A broken rule fails the seed loudly instead of producing data the UI
  can't explain. Trade-off: backdating completions can't go through the service
  layer — the rules are about the present — so those timestamps are written
  directly, the one hand-written exception, and it's commented where it happens.

## Decision 27

- **Chose:** two shells — a manager console with a persistent rail, a technician
  work queue in a narrow column with two destinations.
- **Rejected:** one shell with the manager-only links hidden from technicians.
- **Why:** the two jobs aren't the same job. A manager scans four hundred rows;
  a technician reads one job at a time, and their whole world is `/my-work`.
  The hidden-link version also reads as a product someone has been locked out
  of, which is the wrong impression when the API genuinely has nothing
  fleet-wide to give them. Trade-off: two layouts to keep visually consistent,
  and `landingRouteFor` has to be the single answer to "where does this role
  start" or login and the redirects disagree.

## Decision 28

- **Chose:** every list's filters, sort, page and page size live in the URL.
- **Rejected:** React state inside the page component.
- **Why:** a filtered view is then linkable and survives a reload, the back
  button means what it looks like it means, and the dashboard can deep-link
  into `/services?technician_id=5`. It also makes client-side filtering
  awkward enough that nobody does it by accident — the parameter goes to the
  server or it does nothing. Trade-off: typing in a search box would write a
  history entry per keystroke, so the input keeps its own state and the URL is
  written 300ms after typing stops.

## Decision 29

- **Chose:** the vehicle picker searches the server, ten at a time.
- **Rejected:** fetching the first hundred vehicles and filtering them in the
  browser, which is what the export and new-record dialogs did.
- **Why:** the brief calls out browser-side filtering as the thing not to do,
  and the hundred-row version silently stops working at vehicle 101 — worse
  than failing, because it looks like the vehicle doesn't exist. Trade-off: a
  native `<select>` would have given keyboard behaviour and type-ahead for
  free; a combobox over async options means writing arrow keys, Enter, Escape
  and `aria-activedescendant` by hand.

## Decision 30

- **Chose:** successes are toasted, failures stay inline next to the control
  that failed, carrying the server's own message.
- **Rejected:** one notification mechanism for both.
- **Why:** "Completion odometer 4000 is lower than the vehicle's current
  reading 52300" is the useful half of a rejection, and a message that removes
  itself after four seconds is no way to deliver it. A success has nothing to
  read and shouldn't hold the screen. Trade-off: two patterns to remember when
  adding a mutation.
