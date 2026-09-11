# AI prompts

I used Claude Code throughout, in a loop: write a spec for the next phase, then
implement it. The ones worth recording, in order.

## Setting up the workflow

**Prompt:** a `/create-spec` command defining what a spec must contain — data
model, business rules with their HTTP rejections, permissions, API table, audit
events, tests traceable to the rules, definition of done. Then run it per phase.

**Got:** usable specs. The "risks and open questions" section earned its place
immediately by flagging that the project sat inside an unrelated git repository.

**Corrected:** added "never restate the project rules". The first spec spent a
third of its length repeating the stack and conventions already written down
elsewhere.

## Writing the backend modules

**Prompt:** "write the config, session, model, schema and repository modules."

**Got:** one shell command with nine here-documents. It failed to parse on an
unbalanced quote, and because it was a single command, nothing was written.

**Corrected:** one file per write. Batching is fine for reading, bad for
writing — a single syntax error takes the whole batch down.

## shadcn/ui

**Prompt:** "run `shadcn init` and add the card and skeleton components."

**Got:** an init that exited successfully and did nearly nothing. The CLI has
changed: `--base-color` is gone and `-d` now scaffolds a new project.

**Corrected:** wrote the four files it would have produced —
`components.json`, the `cn` helper, card and skeleton — plus the token palette.
`shadcn add` still works later, because `components.json` is what it needs.

## Proving the health check works

**Prompt:** "start the API against an unreachable database and check `/health`
returns 503."

**Got:** a request that never returned. psycopg waits indefinitely on a host
that drops packets rather than refusing, so the check hung instead of reporting.

**Corrected:** added a connect timeout. Worth remembering: the code looked
right and its unit test passed, because that test used a session raising
immediately. Only a realistically broken dependency showed the bug.

## Installing PostgreSQL locally

**Prompt:** "install PostgreSQL locally so the schema tests run for real."

**Got:** a winget install reporting success with `bin/` but no `lib/`, no data
directory and no service. `initdb` then failed on a missing library.

**Corrected:** used the standalone binaries archive and started a cluster with
`pg_ctl` under my home directory, no admin rights needed.

## The schema

**Prompt:** the schema spec, then "implement it" — models, migration,
constraints, indexes, tests.

**Got:** close to right, and the phase where the spec clearly paid off:
`due_since` and the cycle identifier were there from the first migration rather
than retrofitted.

**Corrected:** two things. `metadata` had to be renamed `event_metadata`,
because it's reserved on SQLAlchemy's declarative base. And the round-trip test
asserted `alembic_version` disappears on `downgrade base` — it doesn't, Alembic
keeps the table and empties it.

## What I verified rather than trusted

- Read the DDL from `alembic upgrade head --sql` before any database existed.
- Tried `UPDATE` and `DELETE` on `audit_events` from raw psql, not just the ORM.
- Left the four tests needing a real database visibly skipping, with a reason,
  until one existed. They weren't called passing before they had run.
