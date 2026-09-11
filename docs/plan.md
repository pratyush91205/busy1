# Plan

## Sessions

Two hours a day, one phase per session, each phase written up as a spec in
`.claude/specs/` before it's built.

| # | Session | Estimated | Actual |
|---|---|---|---|
| 1 | Repo setup and walking skeleton | 2h 00 | 2h 20 |
| 2 | Database schema and migrations | 1h 00 | 1h 30 |
| | Total so far | 3h 00 | 3h 50 |

## Order, and why

Repository shape first, because the project was sitting a directory below the
git root inside an unrelated repo, and fixing that later would have meant
rewriting history. Then the walking skeleton, which satisfies no goal but
everything depends on. Then the schema, all seven tables in one migration
including `audit_events` and the cycle identifier. Authentication comes next,
because the rest of the system is defined by what each role may do.

Tests go in the same session as the rule they cover. No testing phase at the
end — the lifecycle and authorization tests are the ones that matter, and
they'd be first to go if left to last.

## Estimates versus actuals

Session 1 ran 20 minutes over, all of it on the shadcn CLI, whose `init` now
either scaffolds a new project or silently does nothing in an existing one. I
wrote the four files it would have generated instead.

Session 2 ran 30 minutes over getting PostgreSQL running locally. The winget
package installed `bin/` without `lib/`, so `initdb` failed on a missing
library and there was no cluster at all. Switched to the standalone binaries
archive. Writing the schema itself was quick, because the spec had already
settled the awkward parts.

## Cut, and moved

Nothing cut from the ten goals yet.

Deployment moved. It was planned as phase 2, on the reasoning that finding a
broken pipeline at hour 11 is how this fails. I moved it to the end of the build
— trade-off in `decisions.md`. What's already done for it: `render.yaml` is
committed, config is entirely environment-driven, no hard-coded hosts.

If time runs short, the cut order is Playwright tests, then UI polish, then CSV
export conveniences while keeping the export. Not cut: server-side
authorization, lifecycle validation, due/overdue correctness, the audit trail,
per-row bulk reporting.
