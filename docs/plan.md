# Plan

## Sessions

Two hours a day, one phase each, specced in `.claude/specs/` before being built.

| # | Session | Estimated | Actual |
|---|---|---|---|
| 1 | Repo setup and walking skeleton | 2h 00 | 2h 20 |
| 2 | Database schema and migrations | 1h 00 | 1h 30 |
| 3 | Authentication and authorization | 2h 00 | 2h 15 |
| 4 | Vehicle management | 2h 00 | 2h 10 |
| 5 | Service records, lifecycle, audit | 3h 00 | 3h 20 |
| 6 | Due, overdue and alerts | 2h 00 | 2h 30 |
| 7 | Bulk odometer upload and export | 2h 00 | 2h 00 |
| 8 | Dashboard and seed data | 2h 00 | 2h 00 |
| 9 | Frontend experience | 2h 30 | 3h 00 |
| 10 | Deployment | 1h 00 | 0h 45 |
| 11 | Sign-in page | 0h 45 | 0h 45 |
| | Total | 20h 15 | 22h 35 |

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

Session 5, 20 minutes over, and the largest session by far — records,
assignment, lifecycle and audit specced as one piece because every
mutation has to write its audit event in the same transaction. Splitting
them would have meant writing the mutations twice.

Two things cost the time. A whitespace-only description passed
`min_length=1`, stripped to empty in the service layer and hit the
database's not-blank constraint as a 503 — fixed by stripping before the
length check. And I ran two pytest processes against the same test
database at once and spent a while reading the wreckage as a real bug.

Session 6, 30 minutes over, all of it on one thing the spec had wrong.
The mileage half of "is this vehicle due" needs a fixed point to count
from, and there wasn't one: `current_odometer` moves, and 0 would make a
used van due on arrival. That meant a migration mid-spec. I wrote it for
the odometer alone first, then rolled it back and did both columns, since
the date half had the same shape and doing it in one migration is cleaner
than two.

Session 7, on estimate. Two things caught late rather than by a test:
`/services/export.csv` was registered after `/services/{service_id}`, so
it was being read as a service with the id "export.csv"; and
`email-validator` and `python-multipart` were installed into the venv when
the features were written but never added to `requirements.txt`. The suite
runs in that same venv, so it could never have caught the second one — a
fresh deploy would have failed at import.

Session 9, 30 minutes over, and the one session that didn't finish what it set
out to do. The build was fine — the frontend pass landed in six commits and
type-check, lint, production build and pytest all pass. Verification is what
went wrong: the Chrome extension I drive the browser with kept freezing the
renderer, so the manager and technician click-throughs, the 375px check and the
keyboard pass are still not done. Resizing the window unfroze it once, long
enough to log in and confirm the login screen's error state, then it froze
again. The fleet-wide checks I could make without a browser — filter totals and
role scoping through the API — came back right.

The session also found a real bug rather than a polish item: `/services` had
never read `technician_id` or `overdue` out of the URL, so the dashboard's own
"view records" link silently showed the whole fleet instead of that
technician's four.

After session 9, the app was slow enough to notice — five to six seconds for
the dashboard. Measured it rather than guessing: 0.41s per query, the same
for `SELECT 1` as for a count, because the database was in Sydney. Moved it
to a new project in Mumbai (0.028s per query), re-ran the migrations and the
seed. The one snag was a password containing `@`, which has to be
percent-encoded in a connection URI or it gets read as the start of the host.

Then an audit of the ten goals against the brief itself rather than against my
own specs. It found three places where the code did something reasonable that
isn't what the brief says. Booking set a date but not a technician. Sorting by
status sorted the stored strings, so Booked came before Due. And a vehicle past
its interval never became a Due record unless a manager opened one — so it was
never overdue, never alerted, and goal 10's returning alert depended on someone
remembering. That last one was invisible to the suite because every test opened
its records by hand. Fixing it made the dashboard's due tile double-count, so
that changed too (`decisions.md`, 32–34). 257 tests pass, 13 of them new; five
existing ones broke, every one by booking a record with nobody on it — the new
rule doing its job.

After the audit the app was slow again. Measured before changing anything: the
API answered in 0.14–0.9s, and the due-cycle sweep added on reads cost one query
per request, so it wasn't the code. The pages were — 6–8 seconds each and 49 for
`/login` — because `next dev` compiles on request and the machine had 0.8 GB of
its 7.7 free. Served the production build instead: 6–30ms a page. Nothing in the
repository changed.

Session 10, deployment, under estimate. Config had been environment-driven from
the start and the database was already migrated and seeded, so the deploy only
had to ship code. The API went to Railway instead of Render (`decisions.md`,
35). What cost time was the platforms, not the code: Railway refused
`railway.json` as deprecated, so the settings went on the service; Vercel
couldn't see the repository until its GitHub App was installed; and the Vercel
project was imported under a login the assistant couldn't reach, so its API
address had to be set in the dashboard by hand. CORS was set once Vercel had
given the real URL, not guessed.

Session 11, the sign-in page — the plainest screen in the app and the first one
a reviewer sees. Redesigned without changing anything behind it: same form,
validation and errors. Added show password, a Caps Lock warning, a shake on a
refused sign-in, one-click demo accounts (`decisions.md`, 36), and an
illustration of one service cycle.

## Cut

Nothing cut from the ten goals.

Deployment moved from phase 2 to the end of the build (trade-off in
`decisions.md`, 1). Done in session 10, on Vercel and Railway.

If time runs short: Playwright tests go first, then UI polish, then CSV export
conveniences. Not cut: authorization, lifecycle validation, due/overdue
correctness, audit trail, per-row bulk reporting.

Over the 12-hour estimate by about ten and a half hours. The overrun is mostly three
things: a schema change mid-spec in session 6, the size of session 5 —
records, assignment, lifecycle and audit had to be one piece because every
mutation writes its audit event in the same transaction — and session 9,
which was frontend work the first eight sessions had deferred.

Still open: the browser walkthrough of both roles, the narrow-screen check and
the keyboard pass, all blocked on tooling rather than on the code.

Also still open, from an assessment against the brief — both met on the server,
only partly in the interface:

- Goal 5. A technician has no navigation to the one list of every record
  assigned to them. The list exists at `/services`, but their nav links only My
  work, which shows open work and the last five completed.
- Goal 9. The timeline records that a note was added, with who and when, but
  not the note itself; that sits in the Notes panel on the same page.
