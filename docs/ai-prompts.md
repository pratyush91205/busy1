# AI prompts

I used Claude Code throughout, mostly through two repeating steps: write a spec
for the next phase, then implement it. The prompts below are the ones that
mattered, in the order I used them, including the ones that produced something
I had to throw away.

## Setting up a repeatable way of working

### Prompt

I wrote a `/create-spec` command for the project telling the model what a spec
has to contain: data model, business rules with their HTTP rejections,
permissions, API table, audit events, tests traceable to the rules, and a
definition of done. Then I ran it per phase, starting with the walking skeleton.

### What I got

A spec that was usable as-is. The part that paid for itself was the "risks and
open questions" section, which flagged that the project was sitting inside an
unrelated git repository and that the deployment repo name had never been
decided.

### What I corrected

I had to add "never restate the project rules" to the command. The first spec
spent a third of its length repeating the tech stack and error-handling
conventions that were already written down elsewhere, which is noise when the
budget is twelve hours.

## Writing all the backend modules at once

### Prompt

"Write the config, session, model, schema and repository modules for the
walking skeleton."

### What I got

A single shell command containing nine here-documents, one per file. It failed
to parse on an unbalanced quote, and because it was one command, nothing was
written at all. Not a subtle bug, just a bad shape for the job.

### What I corrected

Rewrote it as one file per write. The lesson I kept for later phases: batching
is fine for reading, bad for writing, because a single syntax error takes the
whole batch down and leaves no partial progress to inspect.

## Initialising shadcn/ui

### Prompt

"Run `shadcn init` and add the card and skeleton components."

### What I got

An `init` that exited successfully and did almost nothing. The CLI has changed:
`--base-color` no longer exists, and `-d` now means "scaffold a new project"
rather than "use defaults here". No `components.json`, no `lib/utils.ts`, no
components.

### What I corrected

Stopped fighting the tool and wrote the four files it would have produced:
`components.json`, the `cn` helper, and the card and skeleton primitives, plus
the neutral token palette in `globals.css`. Later phases can still run
`shadcn add`, because `components.json` is what that command actually needs.
This cost about twenty minutes and is the main reason session 1 ran over.

## Proving the health check actually works

### Prompt

"Start the API against an unreachable database and check `/health` returns
503."

### What I got

A request that never returned. psycopg sat waiting on a host that silently drops
packets rather than refusing the connection, so the health check hung instead of
reporting the failure it was written to report.

### What I corrected

Added a five second connect timeout to the engine. This one is worth keeping in
mind, because the code looked right, the test for the 503 path passed (it used a
session that raises immediately), and the bug only appeared when the thing was
run against a realistically broken dependency rather than a mocked one.

## Installing PostgreSQL locally

### Prompt

"Install PostgreSQL locally so the schema tests run against a real database."

### What I got

A winget install that reported success and left a broken installation: `bin/`
present, `lib/` missing, no data directory, no service. `initdb` then failed on
a missing `dict_snowball` library. The custom installer arguments passed for the
superuser password are the likely cause.

### What I corrected

Switched to the standalone binaries archive, initialised a cluster under my home
directory and started it with `pg_ctl`, which needs no administrator rights. The
partial install was left in place, inert.

## Writing the schema

### Prompt

The schema spec, then "implement it": models, the Alembic migration,
constraints, indexes, and the tests.

### What I got

Close to what I wanted, and it is the phase where the spec clearly did its job.
The two things I most wanted right, `due_since` and the service cycle
identifier, were there from the first migration rather than being retrofitted.

### What I corrected

Two things. The audit table's `metadata` column had to be renamed to
`event_metadata`, because `metadata` is reserved on SQLAlchemy's declarative
base. And the first version of the migration round-trip test asserted that
`alembic_version` disappears on `downgrade base`; it does not, Alembic keeps the
table and empties it, so the test now asserts no applied revision instead.

## What I checked rather than trusted

Generated code that touches the data model does not go in on the strength of
looking correct:

- I read the DDL from `alembic upgrade head --sql` by eye before any database
  existed, to confirm the identity column, the `TIMESTAMPTZ` types and the
  `NOT NULL` defaults were what I meant.
- I tried `UPDATE` and `DELETE` on `audit_events` from a raw psql session, not
  only through the ORM, because the ORM proves nothing about what someone else
  can do later.
- The four tests that needed a real database were left visibly skipping, with a
  reason, until the database existed. They were not described as passing before
  they had ever run.
