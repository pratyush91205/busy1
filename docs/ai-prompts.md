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
