# AI prompts

Claude Code throughout, in a loop: spec the next phase, then implement it.

## Setting up the workflow

### Prompt

A `/create-spec` command defining what a spec must contain — data model, rules
with their HTTP rejections, permissions, API table, audit events, tests tied to
the rules, definition of done. Then run it per phase.

### What you got

Usable specs. The "risks and open questions" section immediately flagged that
the project was sitting inside an unrelated git repository.

### What you corrected

Added "never restate the project rules". The first spec spent a third of its
length repeating the stack and conventions already written down elsewhere.

## Writing the backend modules

### Prompt

"Write the config, session, model, schema and repository modules."

### What you got

One shell command with nine here-documents. It failed to parse on an unbalanced
quote, and since it was a single command, nothing was written at all.

### What you corrected

One file per write. Batching is fine for reading, bad for writing.

## Proving the health check works

### Prompt

"Start the API against an unreachable database and check /health returns 503."

### What you got

A request that never returned. psycopg waits indefinitely on a host that drops
packets instead of refusing, so the check hung rather than reporting the failure
it exists to report.

### What you corrected

Added a connect timeout. The code looked right and its unit test passed, because
that test used a session that raises immediately — only a realistically broken
dependency exposed it.

## Installing PostgreSQL and the schema

### Prompt

"Install PostgreSQL locally", then the schema spec and "implement it".

### What you got

A winget install reporting success with `bin/` but no `lib/`, so `initdb` failed
and no cluster existed. The schema itself came out close to right, with
`due_since` and the cycle identifier present from the first migration.

### What you corrected

Used the standalone binaries archive instead, started with `pg_ctl`, no admin
needed. In the schema: renamed `metadata` to `event_metadata` (reserved on
SQLAlchemy's declarative base), and fixed a test that asserted `alembic_version`
disappears on `downgrade base` — Alembic keeps the table and empties it.

## Verified rather than trusted

Read the DDL from `alembic upgrade head --sql` before any database existed;
tried UPDATE and DELETE on `audit_events` from raw psql, not just the ORM; left
the four tests needing a real database visibly skipping until one existed.

## Authentication and authorization

### Prompt

The auth spec, then "implement it". The spec had already settled the parts
worth arguing about: identical answers for a wrong password and an unknown
email, the role re-read from the database rather than taken from the token.

### What you got

Close to right, and two things the spec hadn't decided. bcrypt 5 raises on a
password over 72 bytes rather than truncating it, which nothing had an answer
for. And `useToken` read `localStorage` into state inside an effect — the lint
rule caught it, correctly.

### What you corrected

Split the bcrypt limit two ways: `hash_password` raises, because that input is
an operator seeding a user who should not be handed a silently shortened
password, and `verify_password` returns false, because that input is anonymous
and a login must never be a 500.

Rewrote `useToken` with `useSyncExternalStore`. `localStorage` is an external
store, not React state.

Also moved settings onto `app.state` — `create_app(settings)` had only ever
reached CORS, so a test app would still have verified tokens against whatever
`.env` was on disk.

### Verified rather than trusted

Seeded both roles and drove login, `/auth/me`, a wrong password, an unknown
email, a missing header and a garbage token with curl against the real
database. Checked the stored value really is `$2b$12$` and not the password.
The test that matters signs a token claiming `fleet_manager` for a technician
using the application's own key: it asserts 403, not 401, which is what proves
the token was accepted and the database row overrode the claim.

Not verified: the login form in a browser. The page builds, lints, typechecks
and server-renders its form, and the CORS preflight for both `/auth/login` and
a bearer `/auth/me` was checked with curl — but nobody has clicked it.

## Vehicle management

### Prompt

The vehicle spec, then "implement it". The spec decided up front that archived
vehicles refuse edits, and that paging would be built once here for services to
reuse.

### What you got

Mostly right. `Annotated[PageParams, Query()]` was wrong — FastAPI bound it as
one required query parameter literally called `params`, so every list request
came back 422 before a single filter was exercised.

Separately, batching two commits into one shell command with two heredocs
mangled both: the wrong files in one, the message "Initial commit" on the
other. Same lesson as session 2, relearned.

### What you corrected

Paging became an explicit dependency taking `page` and `limit`. Less clever,
documents both parameters in the OpenAPI schema, and doesn't rest on a FastAPI
version detail.

Reset the two bad commits and redid them one command at a time.

The rule ordering in `update_vehicle` was right first time — validate
everything, then assign — but nothing proved it, so I added the test that
would fail if it were ever reordered: send a lower odometer *and* a valid make
change together, assert 409, then assert the make is unchanged.

### Verified rather than trusted

curl against the local database for each rule: normalisation (` van001 ` stored
as `VAN001`), a technician refused 403 on create, a lower odometer refused 409,
a duplicate refused 409, an archived vehicle refusing an edit, and the default
list hiding archived rows while `include_archived=true` shows them.

That's also how the timezone bug surfaced — `created_at` came back `+05:30`.
Nothing in the test suite compared a timestamp, so no test would have found it.

## Service records, lifecycle and audit

### Prompt

One spec covering records, assignment, lifecycle and audit together, then
"implement it". Specced as one piece deliberately: every mutation has to write
its audit event in the same transaction, so building the mutations first and
the audit trail afterwards means writing them twice.

### What you got

The lifecycle table and the transaction handling came out right. Three things
did not.

A whitespace-only description passed `min_length=1`, stripped to empty in the
service layer, and hit the database's not-blank constraint — a 503 where a 422
belonged.

The vehicle test asserting "no DELETE route exists anywhere" started failing
the moment unassigning a technician was added. The rule was right; the test was
written too wide.

And a `queryClientRef` module-level variable in the service hooks, which is
shared mutable state across renders.

### What you corrected

Stripping moved into a `BeforeValidator` so it runs before the length check.
The constraint stays the guarantee, the schema becomes the readable rejection.

Narrowed the DELETE test to `/vehicles` paths, with a comment saying why
unassignment is legitimately a DELETE.

Replaced the module-level query client with `useQueryClient()` in the hook.

### The mistake that wasn't a bug

Ran a second pytest process while the first was still going, both against the
same test database. Twenty-odd failures that read like a fixture-ordering
disaster — duplicate keys and vanished users at the same time. Nothing was
wrong with the code. Worth remembering that contradictory failures usually mean
the test environment, not the test.

### Verified rather than trusted

Drove the whole workflow against the local database: create vehicle, open a
record, refuse a second open record on the same vehicle, assign, refuse a
technician assigning, refuse Due → Completed, refuse a technician booking,
book, start, note, refuse a completion below the vehicle's odometer, complete,
confirm the odometer moved and `due_since` cleared, open cycle 2, and read the
timeline back — six events, each with the right actor.

The transition table is tested exhaustively rather than by example: all sixteen
ordered pairs, three allowed and thirteen refused. Three happy-path tests would
pass equally well against a service layer that allowed everything.

## Due, overdue and alerts

### Prompt

The spec for due calculation, overdue with a grace period, and alerts with
cycle-scoped dismissal — specced together because dismissal only makes sense
once overdue exists.

### What you got

The overdue half was right first time: derived from status plus `due_since`
plus the grace period, with both passed in rather than read from a module.

The due half was wrong, and the spec was wrong with it. I had written a
`baseline` helper whose two branches returned the same value, which made the
bug obvious on re-reading — but the real problem was underneath: the mileage
comparison needs a fixed point to count from, and nothing stored one.
`current_odometer` can't serve, because it moves and the target runs away.

The SQL `due_predicate` also came out with a dead `if False` branch and muddled
`&`/`|` precedence.

### What you corrected

Added the two baseline columns in a migration, mid-spec. Wrote it for the
odometer alone, then rolled it back and did both columns in one migration since
the date half has the same shape.

Rewrote the predicate as plain integer arithmetic — in PostgreSQL date minus
date is a number of days — so it reads the way the rule is written.

Added the test I actually wanted: the SQL filter and the Python rule are two
implementations of one rule, so a test compares the computed answer for every
vehicle against the filtered set.

### Verified rather than trusted

Drove the whole alert lifecycle against the local database: a vehicle not due,
driven past its mileage interval and becoming due by mileage, a record opened
and inside its grace period, aged nine days and becoming overdue while still
stored as `due`, a technician refused both reading and dismissing, dismissal
clearing the badge while the record stayed overdue, a second dismissal
refused, the cycle completed and both counters reset, cycle 2 opened, and its
alert appearing once aged — with nothing reset or expired to make that happen.

## Bulk odometer upload and CSV export

### Prompt

One spec for both — CSV in and CSV out. They share nothing but their shape, so
the spec says so rather than pretending they're one feature.

### What you got

The non-transactional per-row design came out right, including reusing
`vehicle_service`'s rules rather than writing new ones for CSV.

Three things did not. The row cap was checked *while* iterating, so a 5,001-row
file applied 5,000 rows before refusing — both slow and the wrong answer.
`/services/export.csv` was registered after `/services/{service_id}`, so FastAPI
read it as a service with the id "export.csv". And a test helper borrowed the
app's database session without closing it, which held a transaction open and
made the fixture's TRUNCATE hang the whole run.

### What you corrected

Moved the row cap ahead of any processing — count the lines, refuse the file,
touch nothing.

Registered the reports router before the service router, and wrote a test that
asserts the export route isn't shadowed, so the comment isn't the only guard.

Opened and closed the session explicitly in that test.

Also found, by reading `requirements.txt` against the venv rather than by any
test: `email-validator` and `python-multipart` were never pinned. The suite
runs in the same venv, so it could not have caught it — a fresh deploy would
have failed at import.

### The mistake repeated

Ran a second pytest process while one was still going, again, and then killed
one mid-`downgrade base`, which left the test database half-migrated. Spent
several minutes reading that as a code bug before recognising the shape from
session 5. Two runs must not share one database.

### Verified rather than trusted

Uploaded a mixed CSV against the local database — one good row, one reading
below the stored one, one unknown registration, one archived vehicle — and
confirmed by re-reading the fleet that exactly the good row was applied and the
other three vehicles were untouched. A bad header returned 422 and wrote
nothing; a technician got 403.

Downloaded the export and read it: correct header row, `attachment` disposition,
`text/csv`, ISO-8601 UTC timestamps, two technicians in one cell, and the
derived overdue column reading `yes` for the record that had been aged past the
grace period.

## Dashboard and seed data

### Prompt

The dashboard spec, with the UTC week definition settled up front rather than
left to the implementation — it's the part of this brief most easily got wrong.

### What you got

Close to right. The aggregate queries came out as counts rather than
row-loading, and importing the due and overdue predicates instead of rewriting
them was the right instinct.

Two rough edges: local imports scattered inside functions to dodge a circular
dependency that didn't exist, and a Recharts tooltip formatter typed too
narrowly to compile.

### What you corrected

Hoisted the imports to the top where they belong.

Added the test I actually wanted, which the spec had only implied: assert the
dashboard's overdue count *equals* `GET /alerts/count`, rather than asserting
each is 1. Two numbers over one idea drift; equality catches that and separate
correctness checks don't.

### Verified rather than trusted

Seeded a demo fleet and read the dashboard back: 11 live vehicles and 1
archived, 2 due, 1 overdue, 1 in service, 1 completed this week, all four
statuses populated, all four technicians with work, and six of eight weeks
non-zero. The alert badge returned the same 1 the overdue tile did — the
dismissed second overdue record correctly absent from both.

## Frontend experience

### Prompt

Build the frontend against the existing API and real Supabase data: manager
dashboard with attention items, vehicles, server-side search and filtering on
services, the lifecycle on a service record, a technician "My Work" workflow,
assignment, audit timeline, alerts with a nav badge, CSV import with per-row
results, export, and role-aware navigation. Polished, information-dense, not a
generic SaaS dashboard. Then type-check, lint, build and verify both roles in
the browser.

Specced first, and the spec is the part that paid off: reading the existing
code before writing any turned "build the frontend" into "finish the six
places it is thin and fix the one place it is wrong", which is a much smaller
job than the prompt implies.

### What you got

The spec caught a real defect that a from-scratch rebuild would have papered
over: `/services` read `search`, `status`, `vehicle_id`, `sort` and `page` out
of the URL but not `technician_id` or `overdue`. The dashboard had been
linking to `/services?technician_id=5` since the dashboard existed, and the
list quietly answered with the whole fleet.

The build itself came out close to right — role-split shells, URL-backed
filters, the five status colours as tokens rather than per-component classes.

Two things needed fixing on the way. Heredocs stopped writing files above
about 8KB and silently truncated mid-file, which surfaces as a shell parse
error rather than a bad file; larger components went through the editor tool
instead. And `·` written into JSX *text* is six literal characters, not a
middot — it's only an escape inside a string or template literal.

### What you corrected

Dropped the vehicle filter chip. It needed a registration to display, and the
only one to hand was whatever happened to be in the current page of results —
so with a filter that matched nothing, the chip couldn't name the thing it was
filtering by. The picker already shows the selection and clears it, so the
chip was a second, worse answer to the same question.

Kept the export honest: it takes the query object the table is showing and
strips paging and ordering, rather than exporting page 2 of a filtered view.

### Verified rather than trusted

Type-check, lint and the production build are clean — eleven routes including
`/my-work` — and pytest still passes, which is the check that the frontend
pass didn't touch the backend.

Against the live Supabase data, through the API: 13 service records, 4 for
technician 3, 2 overdue, 3 due; a technician's own list returns 4 and their
requests to `/alerts` and `/dashboard` return 403. That exercises the
parameters the frontend now sends, not the frontend itself.

The browser walkthrough is **not** done, and that is the honest gap in this
session. The extension that drives Chrome kept freezing the renderer — on
example.com as well, so not the app. What did get confirmed visually: the
login screen renders, and pointing it at an unreachable API produces the
network-error state with the API's URL in it. Not confirmed: either role's
click-through, the 375px layout, the keyboard pass.

## Audit against the brief

### Prompt

The ten goals pasted from the brief, with: some of these aren't performing
well — fix what's needed and update the docs.

### What you got

The useful part was the order. It read the code against the brief goal by goal
before changing anything, and came back with four findings rather than a
rewrite: booking set no technician; a vehicle past its interval never became a
Due record on its own; status sorted alphabetically; and, as a consequence of
fixing the second, the dashboard's due tile would count one vehicle in two
tiles. No schema change was needed for any of it.

### What you corrected

Its patch scripts read and wrote files with Python's platform default encoding,
which on Windows is cp1252. One component with real ellipsis characters came
back as mojibake, and the first "repair" decoded the whole file as cp1252 —
correct for the part it had broken, wrong for the part that was fine. Fixed by
mapping the three-byte sequence back; every later patch reads and writes bytes
as UTF-8.

Two near misses caught by its own checks rather than by me: a test patch whose
anchor appeared twice was refused by a uniqueness assert instead of editing the
wrong test, and a pytest run that printed nothing was re-run rather than read as
a pass — an extra `-q` on top of the project's own had made it `-qq`, which
drops the summary line.

### Verified rather than trusted

257 tests pass, 13 new: the booking rules, status sort, and due cycles opening
themselves — including goal 10 end to end, where no test step opens a record by
hand.

Then against the live Mumbai data, after restarting the API onto the new code:
the two vehicles the seed drove past their mileage interval now have Due cycles
the system opened, with a null actor on the timeline; booking one with nobody
assigned is refused 409 with the reason; status sorts in lifecycle order across
all 15 records; and the dashboard's due tile equals the number of vehicles with
a Due record. The browser walkthrough is still not done.
