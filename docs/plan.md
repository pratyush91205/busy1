# Plan

## Sessions

Two hours a day, one phase each, specced in `.claude/specs/` before being built.

| # | Session | Estimated | Actual |
|---|---|---|---|
| 1 | Repo setup and walking skeleton | 2h 00 | 2h 20 |
| 2 | Database schema and migrations | 1h 00 | 1h 30 |
| 3 | Authentication and authorization | 2h 00 | 2h 15 |
| 4 | Vehicle management | 2h 00 | 2h 10 |
| | Total | 7h 00 | 8h 15 |

## Order

Repository shape first — the project sat below the git root in an unrelated
repo, and fixing that later means rewriting history. Then the walking skeleton,
which satisfies no goal but everything depends on. Then the schema, all seven
tables in one migration. Authentication next, because the rest of the system is
defined by what each role may do.

Tests go in the session that introduces the rule. No testing phase at the end;
that's where lifecycle and authorization tests go to die.

## Estimates versus actuals

Session 1, 20 minutes over: the shadcn CLI's `init` now scaffolds a new project
or does nothing, so I wrote the four files it would have generated.

Session 2, 30 minutes over: the winget PostgreSQL package installed `bin/`
without `lib/`, so `initdb` failed and there was no cluster. Switched to the
standalone binaries. The schema itself was quick — the spec had settled the
awkward parts already.

Session 3, 15 minutes over, both on things the spec hadn't decided: bcrypt
refuses passwords over 72 bytes, so hashing and verifying had to answer that
differently (hashing raises at the operator, verifying returns false at the
client). And `useSyncExternalStore` instead of reading `localStorage` into
state in an effect — the lint rule was right, and it's the better hook anyway.

Session 4, 10 minutes over. FastAPI didn't bind a Pydantic model as query
parameters the way I expected, so paging became an explicit dependency —
which documents both parameters properly anyway. Then a curl of a real
response showed timestamps coming back as `+05:30`: TIMESTAMPTZ stores UTC
but renders in the session's timezone. Pinned the session to UTC before the
dashboard's week buckets could inherit the problem.

## Cut

Nothing cut from the ten goals.

Deployment moved from phase 2 to the end of the build (trade-off in
`decisions.md`). Already done for it: `render.yaml`, environment-driven config,
no hard-coded hosts.

If time runs short: Playwright tests go first, then UI polish, then CSV export
conveniences. Not cut: authorization, lifecycle validation, due/overdue
correctness, audit trail, per-row bulk reporting.
