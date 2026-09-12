# Spec 09 - Frontend Experience

## Overview

A redesign-and-complete pass over `apps/web`, so the app reads as a fleet
operations tool rather than a wired-up prototype. It adds no goals: it finishes
the frontend halves of goals 1 to 10 that are thin or missing (technician
workflow, the filters the services list advertises but ignores, attention items
on the dashboard), and gives the whole app one visual system. CLAUDE.md Phase 16
(UI polish, error and loading states) ahead of Phase 17.

No backend or database change. Every screen below is served by an endpoint that
already exists.

## Depends on

Specs 03 to 08, all built. This consumes them and changes nothing behind them.

## Current state

Partial. Every page exists, is client-rendered, reads the real API through
TanStack Query, and keeps filter state in the URL. What is missing or wrong:

* **`/services` ignores `technician_id` and `overdue` in the URL.** The
  dashboard links to `/services?technician_id=5`; the list drops the parameter
  and shows everything. Same for `overdue`. Real bug, not polish.
* Search calls `router.replace` on every keystroke - one history write and one
  request per character.
* No vehicle filter, technician filter, overdue filter, "Last updated" sort
  control, or way to clear filters, on a list whose server supports all of them.
* No technician workflow. A technician is redirected to `/services` and gets the
  manager's table with the buttons removed.
* No attention items on the dashboard - the numbers link out, but nothing says
  which vehicles.
* `/alerts` renders page 1 and has no pager; the endpoint is paginated.
* Export is only on `/reports`, and takes two filters of the five the endpoint
  accepts.
* Vehicle pickers load `limit=100` and filter in the browser.
* Visually flat: two button variants, no toasts, ad-hoc skeletons, one shell at
  `max-w-5xl`, no status colour beyond the badge.

## Data model

No schema changes. No API changes. No new endpoint, parameter or response field.

## Business rules

The frontend enforces nothing - every rule below is the server's, and is
restated only to say what the UI must not contradict.

1. **No client-side filtering, sorting or pagination of a server-paginated
   list.** Every filter control writes a query parameter and re-requests.
   `/services`, `/vehicles` and `/alerts` are read one page at a time.
2. **No frontend-only data.** No placeholder rows, no invented counts, no
   optimistic status that the server has not confirmed. Every number on screen
   came from a response.
3. Overdue is rendered from `is_overdue` on the record. The UI never computes it
   from `due_since` and a guessed grace period, and never treats it as a fifth
   status: filters, sorts and transitions name the four stored values.
4. An action the server would refuse is not offered: booking is manager-only,
   assignment is manager-only, a completed record takes no transition and no
   assignment change. Hiding it is presentation. The 403 or 409 is still the
   answer, and is shown as an inline error rather than swallowed.
5. A rejected transition, assignment, upload row or archive keeps the user where
   they are and shows the server's message verbatim. No generic "Something went
   wrong" over a message that names the conflict.
6. The alert badge count and the alerts list come from the server on every read;
   dismissal re-requests both rather than decrementing a local number.

## Permissions

Server-enforced already; this fixes what the UI *offers*.

**Fleet Manager** - dashboard, fleet-wide vehicles and services, create and edit
vehicles, archive and restore, open service records, assign and unassign
technicians, book, alerts and dismissal, odometer upload, export.

**Technician** - `/my-work` and `/services` (both server-scoped to their
assignments), the service detail of an assigned record, description edits,
notes, and the two transitions they own: In Service and Completed.

**Forbidden, and what the UI does about it** - a technician never sees the
Dashboard, Alerts or Reports nav entries and is redirected off those routes
(403 / 403 / 403 if they navigate anyway); no Book button (403); no assignment
control (403); no vehicle create, edit, archive or restore (403); a service
record they are not assigned to is a 404 and is shown as "not found, or not
assigned to you".

## API

No new endpoints. Newly *consumed* by the frontend, all already implemented:

| Method | Route | Used for | New to the UI |
| --- | --- | --- | --- |
| GET | `/services?technician_id=&overdue=&vehicle_id=&limit=` | filters the list already accepted | yes |
| GET | `/services/export.csv?search=&status=&vehicle_id=&technician_id=&overdue=` | "export this view" from `/services` | yes |
| GET | `/alerts?page=` | pager on the alerts table | yes |
| GET | `/vehicles?search=&limit=10` | server-side vehicle picker | yes |
| GET | `/vehicles?due=true&limit=5` | dashboard attention items | yes |
| GET | `/alerts?limit=5` | dashboard attention items | yes |

Everything else (`/auth/*`, vehicle CRUD, service CRUD, transition, technicians,
notes, timeline, `/dashboard`, odometer upload) keeps its current call sites.

## Audit events

None. This spec issues no new mutations; the existing ones already emit their
events server-side. The timeline is read-only here, and stays read-only - no
edit or delete affordance is added for an audit event or a note.

## Frontend

**Design system** (`app/globals.css`, `components/ui/`). Status tokens for due,
overdue, booked, in-service and completed, defined once and used by badge, row
accent and lifecycle rail. Denser type scale, tabular numerals on every figure,
`focus-visible` ring on every interactive element. Flat surfaces: one border,
no gradient, no glass, no shadow beyond a dialog. Transitions limited to colour
and opacity at 120ms.

**Shell** (`app/(app)/layout.tsx`, `components/app-header.tsx` → nav split).
Manager: persistent left rail at `lg` and above (Dashboard, Vehicles, Services,
Alerts with count, Reports), collapsing to a top bar below it. Technician: top
bar only, two entries (My Work, Vehicles), no rail - the roles should not look
like the same screen with items removed. Skip link, `aria-current` on the active
entry.

**New primitives**: `ui/select`, `ui/toast` (small context toaster, ~80 lines, no
new dependency), `ui/empty-state`, `ui/error-state`, `ui/pagination`,
`ui/sort-button`, `ui/filter-bar`, `hooks/use-debounced-value`,
`components/vehicles/vehicle-picker` (searches the server, 10 at a time).

**Pages**

* `/login` - unchanged behaviour; typography and error placement only.
* `/dashboard` (manager) - four figures, then **Needs attention**: the five
  longest-overdue alerts and the five vehicles due, each row linking to the
  record, each with the one action that clears it. Then status breakdown,
  technician workload, eight-week chart.
* `/vehicles` - denser table, due and archived treated as distinct row states,
  debounced search, sticky header, pager showing the range.
* `/vehicles/[id]` - unchanged information, re-laid out: identity and odometer
  first, next-service second, history last.
* `/services` - the filter bar this list has needed: search (debounced), vehicle
  picker, status, technician (manager only), overdue toggle, active-filter chips
  with clear, three sort columns, page size. **Export this view** for managers.
  Reads and writes every parameter in the URL.
* `/services/[id]` - lifecycle rail with the next step as the primary action,
  assignment inline for managers, notes, timeline. Completed state states why no
  action remains.
* `/my-work` (technician, new) - assignments grouped In Service / Booked / Due,
  each card carrying the transition the technician owns. The technician's landing
  route after login and the redirect target from manager-only routes.
* `/alerts` - days-overdue emphasised, pager, dismissal dialog keeps its wording
  about cycles.
* `/reports` - upload and export side by side; per-row results become a scannable
  table with a failures-first summary line.

**States** - every list has a skeleton matching its own shape, an empty state
that says what would fill it, and an error state carrying the server's message
with a retry. Every mutation reports success as a toast and failure inline.

## Tests

No pytest changes: no backend behaviour changes, and there is no frontend test
runner in this project (Playwright is explicitly optional and out of budget per
CLAUDE.md). Verification for this spec is:

1. `npx tsc --noEmit` clean.
2. `npm run lint` clean.
3. `npm run build` clean.
4. `pytest` still green - proof the backend was not touched.
5. The Success Metric walkthrough in CLAUDE.md, run in the browser against the
   real API and seeded data, as both `manager@fleet.example` and
   `tech@fleet.example`.

## Definition of done

* `/services?technician_id=5` filters by that technician; `/services?overdue=true`
  filters to overdue - both verified against `total` changing.
* Typing in any search box issues one request after the pause, not one per key.
* Every filter, sort, page and page-size survives a reload and is shareable.
* A technician signing in lands on `/my-work`, can start and complete an assigned
  record from it, and sees no Dashboard, Alerts or Reports entry anywhere.
* A technician navigating directly to `/alerts` is redirected, and the API would
  have refused them.
* Manager can assign and unassign from the service detail, and the timeline shows
  both events without a reload.
* Dashboard attention items list real overdue records and real due vehicles, each
  linking to the thing itself.
* Export from `/services` carries the filters currently on screen.
* Odometer upload shows every row's outcome with the server's message.
* Keyboard: tab reaches every action, dialogs trap focus and close on Escape,
  the active nav entry is announced.
* 375px wide: no horizontal page scroll; tables scroll inside their own frame.
* Type-check, lint, build and pytest all pass.

## Risks and open questions

* **Budget.** This is Phase 16 work with all ten goals already built. If it runs
  long, the cut order is: the left rail (keep the top bar for both roles), then
  toasts (inline messages only), then the dashboard attention items. `/my-work`
  and the `/services` filter fixes are not cuttable - one is a required workflow,
  the other is a bug against goal 6.
* **Vehicle picker.** Server-searched at 10 rows solves the `limit=100` ceiling
  for the filter, but the *export* and *new record* dialogs use the same picker,
  so a fleet over 100 vehicles is only correct once all three use it. All three
  will.
* **Decision for the user:** is `/my-work` the technician's landing route, or
  should technicians keep landing on `/services` with `/my-work` as an extra
  page? Spec assumes the former.
