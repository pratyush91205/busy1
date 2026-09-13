# Submission

## Links

- **GitHub repository:** https://github.com/pratyush91205/busy1
- **Live application:** https://busy1-gamma.vercel.app

## Notes for the reviewer

- Neither host sleeps when idle, so the first load shouldn't be slow.
- The sign-in page has one-click buttons for both demo accounts. A manager lands
  on the dashboard, a technician on My work.
- Due and overdue are worked out from the current time, so the numbers move with
  the clock. On 14 September 2026 the fleet had 13 vehicles plus one archived,
  4 due, 1 in service and 1 overdue alert.
- As a technician, the list of every record assigned to you is at `/services`.
  It isn't in the technician navigation yet (goal 5).
- The API is at https://api-production-d13f6.up.railway.app, with interactive
  docs at `/docs`.

## Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Fleet manager | manager@fleet.example | demo1234 |
| Technician | tech@fleet.example | demo1234 |

A second manager (`dana@fleet.example`) and three more technicians
(`alex@`, `priya@`, `tom@fleet.example`) use the same password.

## Stack

| Layer | What you used | Why |
|-------|---------------|-----|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, TanStack Query, React Hook Form with Zod, Recharts | Typed from the API response to the screen. TanStack Query refetches by key after a mutation, so a screen doesn't drift from the server. The browser decides nothing: filters live in the URL and go to the API (`decisions.md`, 28). |
| Backend | FastAPI, Python 3.13, Pydantic, SQLAlchemy 2, Alembic, pytest | Pydantic schemas are the request contract, so a field a role may not send is refused by shape rather than by remembering a check (17). Rules sit in a service layer pytest can call without HTTP (13); 257 tests, all passing. Two languages meant two toolchains and two deploys; that was the price of my preferred stack. |
| Database | PostgreSQL 17 on Supabase | What must hold whatever the code does lives in the database: triggers keep `audit_events` append-only (3), check constraints guard statuses, `(vehicle_id, cycle_number)` is unique. Dashboard figures are aggregate SQL. Mumbai, after measuring 0.41s a query to Sydney against 0.028s (31). |
| Hosting | Vercel (frontend), Railway in Singapore (API), Supabase in Mumbai (database) | Both hosts deploy on push to `main`. Railway only switches to a new deploy once `/health` reaches the database, and Singapore is its nearest region to Mumbai — that matters because one request makes several queries (35). |

## Goal checklist

| # | Goal | Status | Notes |
|---|------|--------|-------|
| 1 | Accounts and roles | Done | Email and password, bcrypt, JWT. The role is re-read from the database on every request, so a tampered claim gets 403 (10). A technician gets 404 for a record not assigned to them (16). |
| 2 | Vehicles | Done | Create, edit, archive, restore. Archived vehicles leave the default list, keep their history, and refuse edits until restored (12). |
| 3 | Service records | Done | The description endpoint accepts a description and nothing else, so an assigned technician can't reassign through it (17). Opening a vehicle lists its service history. |
| 4 | Service lifecycle | Done | One transition function; any other move is refused with 409 and the reason. Booking takes a date and a technician (32). Completing resets both counters from that service's date and odometer (18). Overdue is derived from `due_since` and a 7-day grace period (2, 4). |
| 5 | Assignment | Partial | Many-to-many through `service_technicians`, add and remove are manager-only on the server. Each technician's list of every assigned record exists, scoped by the server, at `/services` — but their navigation only links to My work, so they have to know the URL. |
| 6 | Finding service records | Done | Text search, filters for vehicle, status and technician, sort by scheduled date, status (in lifecycle order) or last update, and pages with a total — all in SQL. |
| 7 | Bulk odometer update and export | Done | CSV by registration number with a result per row. Each row commits on its own, so valid rows land when others are rejected (21). The export streams from a server-side cursor (23). |
| 8 | Dashboard | Done | One endpoint of aggregate queries. ISO weeks in UTC, eight buckets including empty weeks. "Due for service" counts Due cycles not yet booked, so no vehicle sits in two tiles (34). |
| 9 | History you cannot rewrite | Partial | Creation, status changes with old value, new value and actor, assignments, unassignments and notes are appended in the same transaction as the change, and triggers refuse UPDATE and DELETE (3). Partial because the timeline shows that a note was added, by whom and when, but not its text — that sits in the Notes panel on the same page. |
| 10 | Overdue alerts | Done | An alert is an overdue record, and only the dismissal is stored, against that record. One record is one cycle, so the next cycle's alert comes back on its own (2). A vehicle past its interval opens its own Due cycle, with no manager needed (33). The nav badge and the dashboard's overdue tile are tested to agree (25). |

Numbers in brackets are entries in `docs/decisions.md`.

## How much time did you actually spend?

About 22½ hours over eleven sessions, against the 12-hour budget. Session by
session in `docs/plan.md`. Most of the overrun: a schema change mid-way through
session 6, session 5 having to be one piece because every mutation writes its
audit event in the same transaction, and frontend work the earlier sessions had
put off.

## What would you do next, with another 12 hours?

- Close the two partials: a link from the technician navigation to their full
  list (goal 5), and note text in the timeline (goal 9).
- Walk both roles through the live app at desktop and phone width and by
  keyboard, which browser tooling blocked, then cover those journeys with
  Playwright.
- Audit vehicle changes. `audit_events` only holds service events, so who
  archived a vehicle or changed its interval isn't recorded in the database.
- Rate-limit login, and add refresh tokens.

## What are you least happy with in this codebase, and why?

Reads that write. A date interval passes with nothing to trigger on, so alerts,
the dashboard, the lists and the export open any cycles that have fallen due
before they read (33). It's idempotent and dated from the data, so the answer
doesn't depend on when someone looked. But a GET that can insert rows is
surprising, and two requests racing to open the same cycle are only settled by
a unique constraint inside a savepoint. I'd rather reads were pure.

And the frontend has no automated tests. Type-check, lint and the production
build pass, but it has been checked screen by screen and through the API, never
as a full journey for either role.
