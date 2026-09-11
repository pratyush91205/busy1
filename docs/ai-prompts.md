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
