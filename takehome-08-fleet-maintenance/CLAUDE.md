# CLAUDE.md

# Fleet Maintenance System

### A Production-Ready Fleet Service Management Platform

---

## Project Vision

The Fleet Maintenance System is a full-stack application for managing vehicles,
service schedules, technicians, service records, maintenance history, and overdue
service alerts for a logistics fleet.

The goal is not to build a simple CRUD application.

The goal is to build a reliable maintenance management system that can:

1. Authenticate users
2. Enforce role-based permissions
3. Manage fleet vehicles
4. Track vehicle odometers
5. Define service intervals
6. Manage service records
7. Assign technicians
8. Enforce service lifecycle rules
9. Automatically determine due and overdue services
10. Maintain immutable service history
11. Provide server-side search, filtering, sorting and pagination
12. Process bulk odometer updates
13. Generate service history exports
14. Provide fleet management dashboards
15. Generate and manage overdue alerts

The system should behave like a small production fleet-management product,
not a demonstration CRUD application.

---

# Core Principle

Every feature should contribute to one of these capabilities:

* Manage
* Track
* Enforce
* Audit
* Inform

Avoid features that only add visual complexity.

Prioritize correctness of business rules over unnecessary UI features.

The backend is the source of truth.

Never rely on the frontend to enforce authorization,
service lifecycle rules, odometer validation, or business constraints.

---

# Protected Files

These files are owned by the user, not by Claude.

Claude must NEVER create, edit, overwrite or delete:

* README.md
* SUBMISSION.md
* docs/architecture.md
* docs/schema.md
* docs/plan.md
* docs/decisions.md
* docs/ai-prompts.md

These are assessed deliverables. The user is accountable for them in an
interview, so the user writes them.

Claude's role for these files is to DRAFT content and hand it over:

1. Write the draft to the scratchpad, or output it in chat.
2. Say which file it belongs in.
3. Let the user review, edit and commit it.

Never write to these paths directly, even when asked to "update the docs",
unless the user explicitly lifts this restriction for a named file.

Everything else in the repository is Claude's to create and edit normally.

---

# Time Budget

The total budget for this assignment is approximately 12 hours,
spent roughly 2 hours a day across a week.

This constraint outranks polish.

Consequences that must be respected:

* Ten goals met solidly beats ten goals half-built.
* Eight goals done well beats ten goals done badly.
* Do not start optional stretch features until all ten required goals are done.
* Do not gold-plate the UI while a required business rule is unimplemented.

The stack below is a two-language stack (TypeScript + Python).
That doubles setup, dependency and deployment overhead against a
single-language alternative, and the brief awards nothing for stack choice.
It is kept because it is the user's stated preference, but the cost is real:
early phases must stay tight, and the deployment pipeline must be proven
early rather than discovered late.

If time runs short, cut in this order:

1. Optional stretch features
2. Playwright / end-to-end tests
3. UI polish and advanced loading states
4. CSV export niceties (keep the export itself)

Never cut:

* Server-side authorization
* Service lifecycle validation
* Due / overdue correctness
* Immutable audit history
* Per-row bulk odometer reporting

---

# Tech Stack

Frontend:

* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui
* TanStack Query
* React Hook Form
* Zod
* Recharts

Backend:

* FastAPI
* Python 3.12
* Pydantic
* SQLAlchemy
* Alembic

Database:

* PostgreSQL

Authentication:

* JWT-based authentication
* Secure password hashing

Testing:

* Pytest - required, focused on business rules
* Playwright - OPTIONAL, only if all ten goals are complete with time left

File Processing:

* Python CSV module
* Pandas only where useful for bulk processing

Deployment:

* Vercel — frontend
* Render — backend
* Supabase — PostgreSQL

Version Control:

* Git
* GitHub

---

# Project Structure

fleet-maintenance/
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   └── ...
│   │
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── repositories/
│       │   ├── auth/
│       │   ├── utils/
│       │   └── main.py
│       │
│       ├── migrations/
│       └── tests/
│
├── docs/
│   ├── architecture.md
│   ├── schema.md
│   ├── plan.md
│   ├── decisions.md
│   └── ai-prompts.md
│
├── README.md
├── SUBMISSION.md
├── CLAUDE.md
└── .gitignore

---

# Development Philosophy

Follow these rules strictly:

1. Keep modules small and focused.
2. Prefer composition over unnecessary inheritance.
3. Avoid unnecessary abstractions.
4. Every service should have a single responsibility.
5. Keep business logic out of API route handlers.
6. Prefer type safety everywhere.
7. Avoid code duplication.
8. Validate all user input.
9. Keep authorization on the server.
10. Never trust frontend permissions.
11. Use database constraints where appropriate.
12. Use transactions for multi-step operations.
13. Never silently ignore errors.
14. Never introduce mock implementations unless explicitly requested.
15. Do not over-engineer the system.
16. Build the required assignment functionality before optional features.
17. Write tests for important business rules.
18. Keep the code understandable enough to explain during an interview.
19. Prefer simple solutions over complex infrastructure.
20. Document meaningful architectural decisions.

---

# Domain Architecture

The system contains the following primary domain entities:

1. User
2. Vehicle
3. ServiceRecord
4. ServiceTechnician
5. ServiceNote
6. AuditEvent
7. OverdueAlert

Core relationships:

User
│
├── Fleet Manager
└── Technician

Vehicle
│
└── Service Records

Service Record
│
├── Vehicle
├── Technicians
├── Notes
└── Audit Events

Technician
│
└── Many Service Records

A service record belongs to exactly one vehicle.

A service record can have multiple technicians.

A technician can be assigned to multiple service records.

---

# User Roles

The system has two primary roles.

## Fleet Manager

Fleet managers can:

* Create vehicles
* Edit vehicles
* Archive vehicles
* Restore vehicles
* Configure service intervals
* Create service records
* Assign technicians
* Remove technicians
* View the entire fleet
* Bulk update odometer readings
* Export service history
* View dashboard statistics
* View overdue alerts
* Dismiss overdue alerts

## Technician

Technicians can:

* View service records assigned to them
* View their assigned records across all vehicles
* Update permitted service information
* Add notes
* Perform permitted lifecycle actions

Technicians cannot:

* Create vehicles
* Edit service intervals
* Archive vehicles
* Restore vehicles
* Assign technicians
* Remove technicians
* Reassign service records

These restrictions MUST be enforced on the backend.

Never implement authorization by simply hiding buttons in the frontend.

---

# Authentication and Authorization

Authentication must be implemented server-side.

Users authenticate using:

* Email
* Password

Passwords must never be stored in plain text.

Use secure password hashing.

Every protected API request must identify the authenticated user.

Authorization must be checked for every protected operation.

Use role-based authorization.

Example:

Manager:
POST /vehicles
→ allowed

Technician:
POST /vehicles
→ 403 Forbidden

Technician:
POST /services/{id}/technicians
→ 403 Forbidden

Manager:
POST /services/{id}/technicians
→ allowed

Never trust:

* frontend route restrictions
* hidden buttons
* client-side role checks
* user-provided role fields

The server determines the user's actual role.

---

# Vehicle Management

A vehicle contains:

* id
* registration_number
* make
* model
* current_odometer
* service_date_interval
* service_mileage_interval
* is_archived
* created_at
* updated_at

Fleet managers can:

* Create vehicles
* Edit vehicles
* Archive vehicles
* Restore vehicles

Registration numbers should be unique.

Odometer readings must never move backwards.

Archiving is a soft-delete operation.

Never physically delete a vehicle when it is archived.

Vehicle service history must remain accessible.

Default fleet views should exclude archived vehicles unless explicitly requested.

---

# Service Records

Every service record belongs to exactly one vehicle.

A service record contains at minimum:

* id
* vehicle_id
* description
* status
* scheduled_date
* created_at
* updated_at

Who may edit what on a service record:

* A Fleet Manager creates the record.
* Any technician currently assigned to the record may edit its description.
* A Fleet Manager may also edit the description.
* NOBODY except a Fleet Manager may change who is assigned.
* An assigned technician editing the description must not be able to
  smuggle an assignment change through the same request.

Enforce this by keeping the description-update endpoint and the
assignment endpoints strictly separate. The description-update schema
must not accept a technician list, a vehicle_id, or a status field.

A service record can have multiple assigned technicians.

Use a many-to-many relationship through:

service_technicians

Do not store technician IDs as a comma-separated string
or JSON array inside the service record.

---

# Service Lifecycle

The service lifecycle is:

Due
↓
Booked
↓
In Service
↓
Completed

Only valid state transitions are allowed.

Valid transitions:

Due → Booked
Booked → In Service
In Service → Completed

Invalid transitions must be rejected by the server.

Examples:

Due → Completed
→ reject

Due → In Service
→ reject

Completed → Booked
→ reject

Completed → In Service
→ reject

Never allow the frontend to determine whether a transition is valid.

Implement centralized transition validation.

Example:

validate_service_transition(
    current_status,
    requested_status
)

If a transition is invalid, return a clear error explaining why.

---

# Service Due Calculation

A vehicle becomes due for service when either:

1. The date interval has been reached
OR
2. The mileage interval has been reached

Whichever condition occurs first makes the vehicle due.

Date condition:

today >= last_completed_service_date + service_date_interval

Mileage condition:

current_odometer >= last_completed_service_odometer
                    + service_mileage_interval

Both conditions must be evaluated.

Do not require both conditions to be satisfied.

The system must use the most recent completed service
as the starting point for the next service cycle.

---

# Service Completion

When a service is completed:

1. Record completion timestamp.
2. Record the completion odometer.
3. Reset the service date counter.
4. Reset the service mileage counter.
5. Start the next service cycle.
6. Create an immutable audit event.
7. Update related dashboard data.
8. Resolve or invalidate the previous service cycle's overdue state.

The next service interval starts from:

last completed service date

AND

last completed service odometer.

Do not calculate future service intervals from the original vehicle creation date.

---

# Overdue Rules

A service becomes overdue when:

1. It is Due.
2. It remains unbooked.
3. The grace period has elapsed since it became Due.

## Grace period definition

The grace period is 7 days.

It is a single global value, not per-vehicle.

It is configured through the environment variable:

OVERDUE_GRACE_PERIOD_DAYS=7

The application reads it at startup with a default of 7 if unset.

Overdue condition:

now >= due_since + OVERDUE_GRACE_PERIOD_DAYS
AND status == Due

where due_since is the timestamp at which the record first became Due
for the current service cycle.

Persist due_since on the service record. Do not recompute it from
interval arithmetic on every read, or the overdue clock will silently
shift whenever a vehicle's intervals are edited.

Overdue is a DERIVED state, not a fifth lifecycle status.

The status column stores only: Due, Booked, In Service, Completed.
Overdue is computed from status + due_since + the grace period.
Do not add an Overdue value to the status enum.

Overdue status must be determined from the current service cycle.

The system must not depend entirely on a scheduled background job
to determine whether a vehicle is overdue.

The current state should be derivable from persisted data and the current time.

If background jobs are introduced later, they should improve notification behavior,
not become the only source of truth for maintenance state.

---

# Technician Assignment

Technician assignments are many-to-many.

Use:

service_technicians

Example:

Service 101
├── Technician A
├── Technician B
└── Technician C

Technician A
├── Service 101
├── Service 205
└── Service 301

Only Fleet Managers can:

* Add technicians
* Remove technicians

Technicians cannot modify assignments.

Every technician must have a server-filtered list
containing all records assigned to them across all vehicles.

---

# Service Search and Filtering

Service listing must support server-side:

* Text search
* Vehicle filter
* Status filter
* Technician filter
* Sorting
* Pagination

Supported sorting:

* Scheduled date
* Status
* Last updated

Example:

GET /services?
    search=brake
    &vehicle_id=12
    &status=Due
    &technician_id=5
    &sort=scheduled_date
    &page=2
    &limit=20

Never:

1. Load every service into the browser.
2. Filter them using JavaScript.
3. Paginate the filtered array.

Filtering, sorting and pagination must happen in PostgreSQL
through the backend.

Return pagination metadata such as:

* total
* page
* limit
* total_pages

---

# Database Standards

Use PostgreSQL as the primary database.

Use SQLAlchemy for database access.

Use Alembic for migrations.

Use foreign keys for relationships.

Use database constraints wherever appropriate.

Important constraints include:

* Unique vehicle registration number
* Valid foreign keys
* Non-negative odometer values
* Valid user roles
* Valid service statuses
* Valid technician assignments

Use indexes for frequently queried fields.

Likely indexes include:

* vehicles.registration_number
* vehicles.is_archived
* service_records.vehicle_id
* service_records.status
* service_records.scheduled_date
* service_records.updated_at
* service_technicians.technician_id
* service_technicians.service_id
* audit_events.service_id

Do not prematurely optimize.

Only introduce denormalization when there is a clear reason.

---

# Odometer Updates

Fleet managers can upload CSV files containing:

vehicle registration number
odometer reading

The vehicle identifier in the CSV is the REGISTRATION NUMBER,
not the internal database id. A fleet manager uploading readings from
the depot knows the registration plate, not a surrogate key.

Required header, exactly:

registration_number,odometer

Example:

registration_number,odometer
VAN001,52300
VAN002,76100
VAN003,45000

Reject the whole upload only for a malformed or missing header.
Every other failure is a per-row rejection.

For every row:

1. Validate the row.
2. Find the vehicle.
3. Compare the new reading against the latest recorded reading.
4. Reject the row if the new reading is lower.
5. Update valid readings.
6. Continue processing other rows even when one row fails.

Bulk processing must NOT use all-or-nothing transaction semantics.

Valid rows must still succeed when other rows fail.

Return a per-row result.

Example:

Row 1
SUCCESS
Vehicle VAN001 updated to 52300

Row 2
REJECTED
New reading 76000 is lower than existing reading 76500

Row 3
SUCCESS
Vehicle VAN003 updated to 45000

---

# Odometer History

DECIDED: there is no separate odometer history table.

vehicles.current_odometer IS the most recently recorded reading.
It is the single source of truth for odometer validation.

Rationale:

* The brief requires rejecting a reading lower than the vehicle's most
  recently recorded one. current_odometer satisfies that directly.
* The odometer needed for service cycle maths is the completion odometer,
  which is already stored on the completed service record.
* A history table adds a migration, a repository and a join for no
  requirement in the brief, against a 12-hour budget.

Draft this for docs/decisions.md as a real decision with its trade-off:
the per-reading audit trail is lost, so a mistaken-but-higher reading
cannot be traced back to the CSV row that introduced it.

Validation rules:

* A reading lower than current_odometer is ALWAYS rejected.
* A reading equal to current_odometer is accepted as a no-op success.
* A reading higher than current_odometer updates it.
* current_odometer is monotonically non-decreasing. Enforce non-negativity
  with a CHECK constraint in the database, and the comparison rule in
  the service layer.

If the user later asks for per-reading auditing, introduce an
odometer_readings table and make it the source of truth consistently.
Do not half-introduce it.

---

# CSV Export

Provide service history export as CSV.

The export must include:

* Vehicle
* Service record
* Relevant dates
* Status
* Other useful service information

The export must be generated from the backend.

Do not generate the complete report by loading all records into the browser.

Use streaming or efficient server-side generation if the dataset becomes large.

---

# Immutable Audit Timeline

Every service record must have an immutable timeline.

Audit events include:

* Service created
* Status changed
* Technician assigned
* Technician unassigned
* Note added

Status events must contain:

* Old status
* New status
* Actor
* Timestamp

Assignment events must contain:

* Technician
* Actor
* Timestamp

Notes must contain:

* Author
* Content
* Timestamp

Audit records MUST NOT be editable.

Audit records MUST NOT be deletable.

This restriction applies even to Fleet Managers.

Never expose a generic update or delete endpoint for audit events.

Audit history is append-only.

---

# Audit Event Design

Use a dedicated audit_events table.

Example:

audit_events
------------
id
service_id
actor_id
event_type
old_value
new_value
metadata
created_at

Audit events should be created inside the same transaction
as the operation they describe whenever possible.

For example:

Status update
    ↓
Update service status
    ↓
Create audit event
    ↓
Commit transaction

Do not update the service successfully while silently failing
to create its audit record.

---

# Notes

Service notes are append-only.

Technicians can add notes to records assigned to them.

Fleet managers can view service notes.

Notes should contain:

* id
* service_id
* author_id
* content
* created_at

Do not silently overwrite previous notes.

If editing/deleting notes is not explicitly required,
do not implement it.

---

# Overdue Alerts

When a service becomes overdue:

1. Create or expose an overdue alert.
2. Display it in the alerts area.
3. Show an alert count in navigation.
4. Allow Fleet Managers to dismiss the alert.

A dismissed alert belongs to a specific service cycle.

Do not treat dismissal as permanently suppressing
all future alerts for the vehicle.

When the vehicle enters a new service cycle,
becomes due again,
and remains unbooked beyond the grace period,
a new overdue alert must appear.

Use a cycle identifier or equivalent mechanism
to distinguish separate service cycles.

---

# Dashboard

The Fleet Manager dashboard must display:

* Vehicles due for service
* Vehicles currently in service
* Services completed this week
* Vehicles overdue for service

Also display:

* Service records by status
* Service records by technician
* Services completed per week for the last eight weeks

## Time handling

All timestamps are stored in UTC as timezone-aware columns.

All week boundaries are computed in UTC.

A week runs Monday 00:00:00 UTC to Sunday 23:59:59 UTC (ISO-8601 weeks).

"Services completed this week" means the ISO week containing now, in UTC.

"Services completed per week for the last eight weeks" means the eight
ISO weeks ending with the current one, including weeks with a zero count.
Do not omit empty weeks - the chart must show eight buckets.

Apply the same UTC rule to service date-interval arithmetic and to the
overdue grace period, so due dates, overdue flags and dashboard counts
never disagree with each other.

Dashboard calculations should happen server-side.

Do not load all service records into the frontend
just to calculate dashboard metrics.

Use optimized aggregate SQL queries.

---

# Frontend Standards

Use Next.js and TypeScript.

Prefer Server Components where appropriate.

Use Client Components only when interaction requires them.

Use TanStack Query for server state where useful.

Use React Hook Form and Zod for complex forms.

Pages:

* Login
* Dashboard
* Vehicles
* Vehicle Details
* Services
* Service Details
* Technicians
* Alerts
* Reports

Technician users should see a simplified interface
focused on their assigned service records.

Fleet Managers should have access to fleet-wide functionality.

---

# UI Principles

The UI should feel like:

Fleet Management × Linear × modern admin dashboard

Requirements:

* Clean
* Professional
* Fast
* Technical
* Responsive
* Information-dense
* Easy to scan

Avoid:

* Excessive animations
* Decorative UI with no functional purpose
* Giant unnecessary cards
* Excessive gradients
* Overly complicated navigation

Prioritize clarity.

Important information should be visible immediately.

Use consistent:

* Status badges
* Tables
* Filters
* Empty states
* Loading states
* Error states
* Confirmation dialogs
* Toast notifications

---

# Status Visualization

Use consistent visual indicators for:

Due
Booked
In Service
Completed
Overdue
Archived

Note what these are underneath.

Due, Booked, In Service and Completed are the four stored lifecycle
statuses. Overdue and Archived are DERIVED and rendered as badges only:

* Overdue is computed from status Due + due_since + the grace period.
  It is not a value in the status enum. See Overdue Rules.
* Archived comes from vehicles.is_archived, not from service status.

A record that is Overdue is still stored as Due. The UI may show the
Overdue badge in place of the Due badge, but any filter, transition or
API contract that names a status still uses the four stored values.

Do not rely only on color.

Status badges should contain readable text.

Example:

[ DUE ]

[ BOOKED ]

[ IN SERVICE ]

[ COMPLETED ]

[ OVERDUE ]

---

# Vehicle Details

Opening a vehicle should show:

Vehicle information
↓
Current odometer
↓
Service interval configuration
↓
Current maintenance state
↓
Next service information
↓
Service history
↓
Relevant alerts

Archived vehicles should retain their history.

---

# Service Details

Opening a service record should show:

* Vehicle
* Description
* Status
* Scheduled date
* Assigned technicians
* Notes
* Audit timeline

The service lifecycle should be visually clear.

Example:

Due
  ↓
Booked
  ↓
In Service
  ↓
Completed

Highlight the current state.

Only display actions that the current user
is actually allowed to perform.

Remember that hiding an action is not authorization.

The backend must still enforce the rule.

---

# API Architecture

Use:

api/
services/
repositories/
models/
schemas/

Structure:

API Route
    ↓
Authorization
    ↓
Service Layer
    ↓
Repository Layer
    ↓
Database

API routes should remain thin.

Do not place business logic directly inside route handlers.

Example:

POST /services/{id}/complete

should call something like:

service_service.complete_service(
    service_id,
    actor
)

The service layer handles:

* Validation
* State transition
* Completion data
* Audit event
* Related maintenance state

---

# Backend Error Handling

Return meaningful HTTP errors.

Examples:

400 Bad Request
→ Invalid input

401 Unauthorized
→ User is not authenticated

403 Forbidden
→ User does not have permission

404 Not Found
→ Resource does not exist

409 Conflict
→ Business conflict such as invalid state transition
or duplicate registration number

422 Unprocessable Entity
→ Validation failure

Errors should contain a useful message.

Never silently fail.

---

# Business Rule Validation

Business rules must live in the backend service layer.

Examples:

* Technician cannot create vehicle.
* Technician cannot change service interval.
* Technician cannot assign another technician.
* Service cannot skip lifecycle states.
* Odometer cannot decrease.
* Archived vehicle cannot appear in default fleet view.
* Audit event cannot be edited.
* Audit event cannot be deleted.
* Overdue alert dismissal must be cycle-specific.

Do not duplicate critical business rules only in frontend code.

Frontend validation improves UX.

Backend validation guarantees correctness.

---

# Transactions

Use database transactions for operations that modify
multiple related records.

Example:

Completing a service:

BEGIN
    update service status
    record completion data
    create audit event
    update maintenance cycle
COMMIT

If a critical part fails:

ROLLBACK

Do not leave the database in a partially updated state.

---

# Testing Strategy

Focus testing effort on business rules.

WHEN: tests are written in the same phase as the rule they cover, and in
the same commit or the one immediately after. There is no late testing
phase. A rule shipped without its test is not done.

Pytest is required. Playwright is optional and only after all ten goals.

Required tests include:

## Authentication

* Valid login
* Invalid password
* Unknown user
* Protected endpoint without authentication

## Authorization

* Manager can create vehicle
* Technician cannot create vehicle
* Manager can assign technician
* Technician cannot assign technician
* Technician only sees assigned services

## Service Lifecycle

Due → Booked
Booked → In Service
In Service → Completed

Invalid transitions must fail.

## Odometer

50,000 → 51,000
→ success

50,000 → 49,000
→ rejection

Bulk CSV:

Valid rows succeed
Invalid rows fail
Valid rows are not rolled back because another row failed

## Due Calculation

Date interval reached
→ Due

Mileage interval reached
→ Due

Neither reached
→ Not Due

## Overdue

Due + grace period exceeded + not booked
→ Overdue

Dismiss alert
→ Current alert dismissed

New service cycle + overdue
→ New alert appears

## Audit

Status change creates audit event.

Assignment creates audit event.

Unassignment creates audit event.

Note creation creates audit event.

Audit event cannot be modified.

Audit event cannot be deleted.

---

# Security Rules

Never:

* Store plain-text passwords.
* Expose password hashes to the frontend.
* Expose secrets in API responses.
* Commit environment variables.
* Trust frontend authorization.
* Accept arbitrary role changes from clients.
* Allow technicians to access unauthorized records.
* Allow audit history to be modified.
* Log sensitive credentials.

Use:

* Environment variables
* Secure password hashing
* Backend authorization
* Input validation
* Parameterized database queries
* HTTPS in production

---

# Environment Variables

Never commit secrets.

Use:

DATABASE_URL=
JWT_SECRET=
CORS_ORIGINS=
OVERDUE_GRACE_PERIOD_DAYS=7

OVERDUE_GRACE_PERIOD_DAYS is not a secret, but it is configuration and
belongs here rather than hard-coded in the service layer. Default to 7
when unset so a missing value never silently disables overdue detection.

Development:

.env

Production:

Provider-managed environment variables.

Add:

.env

to .gitignore.

---

# Seed Data

The deployed application must contain meaningful demo data.

Seed:

* Fleet Managers
* Technicians
* Vehicles
* Service records
* Technician assignments
* Different lifecycle states
* Due vehicles
* Overdue vehicles
* Completed services
* Audit history
* Notes

The dashboard should look populated immediately after deployment.

---

# Demo Accounts

Provide demo credentials for:

Fleet Manager

Technician

Record the credentials in:

SUBMISSION.md

Never commit real production credentials.

---

# Documentation

Documentation is written CONTINUOUSLY, not at the end.

The brief is explicit: fill these in as you go, not from memory at the end.
plan.md wants estimated versus actual time per session, and ai-prompts.md
wants the prompts in the order they were used including the ones that went
wrong. Neither is reconstructable afterwards.

At the end of every working session, Claude drafts the session's additions
to plan.md, decisions.md and ai-prompts.md and hands them to the user.

REMINDER: every file under docs/ is a Protected File.
Claude drafts the content and gives it to the user.
Claude does not write to docs/ directly.
See the Protected Files section.

The files the user maintains:

docs/
├── architecture.md
├── schema.md
├── plan.md
├── decisions.md
└── ai-prompts.md

## architecture.md

Explain:

* System components
* Frontend
* Backend
* Database
* Request flow
* Authentication
* Authorization
* Business logic
* Deployment architecture
* What was deliberately not built

## schema.md

Document:

* Every table
* Columns
* Data types
* Primary keys
* Foreign keys
* One-to-many relationships
* Many-to-many relationships
* Database constraints
* Indexes
* Denormalization
* Scaling considerations

## plan.md

Track:

* Development sessions
* Estimated time
* Actual time
* Implementation order
* What changed
* What was cut

## decisions.md

Document at least five real decisions.

Each decision should include:

* Problem
* Options considered
* Chosen solution
* Why it was chosen
* Trade-offs

At least one decision should document a decision
that was later reversed.

## ai-prompts.md

Record the actual AI prompts used during development.

Include:

* Useful prompts
* Bad prompts
* Incorrect generated solutions
* What was changed afterward
* Why the final solution was preferred

Never claim AI-generated code was correct without verification.

---

# SUBMISSION.md

SUBMISSION.md is the first file the reviewer opens.

It is a Protected File. Claude never edits it.
Claude may draft content for the user to paste in.

It must end up containing:

* Public GitHub repository URL
* Live deployed application URL
* A note if the host sleeps when idle and the first load is slow
* Demo credentials for BOTH roles (Fleet Manager and Technician)
* The stack table, with a reason per layer
* An honest per-goal checklist for all ten goals,
  marked Done / Partial / Not done, with notes on anything partial
* Actual time spent
* What would come next with another 12 hours
* What the user is least happy with in the codebase, and why

Mark goals honestly. A goal marked Partial with a clear note reads far
better than one marked Done that the reviewer finds broken.

Demo credentials must be seeded demo accounts, never real credentials.

---

# Git Standards

Commit incrementally.

Do not build the entire application
and create one final commit.

The repository is not yet a git repository.

The very first action of Phase 1 is:

git init
git remote add origin <public GitHub repo>
git commit  (project skeleton)

A history that is one "initial commit" containing a finished app
scores zero on git history and colours how everything else is read.

Commit after each meaningful step, not once per phase.

A phase normally produces SEVERAL commits. For example, Phase 8
(service lifecycle) should produce something like:

* feat: add service status enum and transition table
* feat: enforce lifecycle transitions in service layer
* test: cover valid and invalid lifecycle transitions
* feat: emit audit events on status change
* feat: reset service counters on completion

Aim for roughly 40 to 60 commits across the whole build, not 16.

Commit messages should describe meaningful changes.

Examples:

feat: add vehicle management

feat: enforce service lifecycle transitions

feat: add technician assignments

feat: implement overdue alerts

test: add service lifecycle tests

fix: reject decreasing odometer readings

---

# MVP Scope

The MVP must include all ten required assignment goals.

Required:

* Authentication
* Fleet Manager role
* Technician role
* Server-side authorization
* Vehicle CRUD
* Vehicle archive/restore
* Service intervals
* Service records
* Technician assignment
* Service lifecycle
* Due calculation
* Overdue calculation
* Grace period
* Server-side search
* Server-side filtering
* Server-side sorting
* Server-side pagination
* Bulk odometer CSV
* Per-row bulk result reporting
* Service history CSV export
* Dashboard
* Immutable audit timeline
* Overdue alerts
* Alert dismissal
* Alert reappearance for a new service cycle

Optional stretch features are secondary.

Do not implement optional features
until all required functionality is complete.

---

# Success Metric

A Fleet Manager should be able to:

1. Log in
2. View the fleet dashboard
3. Create a vehicle
4. Configure its service intervals
5. Create a service record
6. Assign one or more technicians
7. See the service become Due when an interval is reached
8. Book the service
9. Move it to In Service
10. Complete the service
11. See the service history updated
12. See both service counters reset
13. View the complete audit timeline
14. Receive an overdue alert when applicable
15. Dismiss the alert
16. See a future service cycle generate a new alert
17. Upload bulk odometer readings
18. Receive per-row success/failure results
19. Search and filter services server-side
20. Export service history

A Technician should be able to:

1. Log in
2. See only assigned service records
3. See assignments across vehicles
4. Update permitted service information
5. Add notes
6. Perform permitted lifecycle actions

A Technician must not be able to:

* Create vehicles
* Modify service intervals
* Assign technicians
* Remove technicians
* Access unauthorized service records

If this workflow works end-to-end,
the core MVP is successful.

---

# Implementation Priorities

Priority order:

CRITICAL
* Working deployment pipeline, proven early
* Database
* Authentication
* Authorization
* Vehicles
* Service records
* Technician assignments
* Service lifecycle
* Due/overdue calculation
* Audit history
* Tests for the business rules above

HIGH
* Server-side search
* Filtering
* Sorting
* Pagination
* Bulk odometer updates
* Alerts
* Dashboard

MEDIUM
* CSV export
* UI polish
* Advanced loading states
* Advanced error handling

LOW
* Optional stretch features

Do not sacrifice critical business correctness
for visual polish.

---

# Development Order

Follow this dependency order.

Three rules override the phase list and apply throughout:

1. TESTS ARE WRITTEN INSIDE THE PHASE THEY COVER, never batched at the end.
   The lifecycle, odometer, authorization and due/overdue tests are the
   ones that demonstrate judgement. They are also the first casualty of a
   late testing phase, which is exactly why they are not given one.

2. AUDIT EVENTS ARE EMITTED FROM THE FIRST COMMIT OF EACH MUTATION.
   Not retrofitted. A mutation and its audit event are written together,
   in the same transaction, in the same commit.

3. DOCUMENTATION IS DRAFTED AT THE END OF EVERY SESSION, not at the end
   of the project. See the Documentation section.

Phase 1
Project setup + git init + public GitHub repo + first commit
↓
Phase 2
Deployment pipeline walking skeleton
Prove Supabase + Render + Vercel end to end with a hello-world that
reads one row from the database and renders it in the browser.
This is the single highest-risk step in the project. Doing it now means
every later phase ships to a live URL. Doing it at hour 11 is how this
assignment fails with the app already written.
↓
Phase 3
Database schema + migrations
Includes audit_events and the service cycle identifier from the start,
so neither has to be retrofitted later.
↓
Phase 4
Authentication + authorization (+ tests in phase)
↓
Phase 5
Vehicle management + archive/restore + intervals (+ tests in phase)
↓
Phase 6
Service records (+ audit events emitted from the first commit)
↓
Phase 7
Technician assignment (+ audit events emitted from the first commit)
↓
Phase 8
Service lifecycle + transition validation + counter reset
(+ audit events, + tests in phase)
↓
Phase 9
Due + overdue calculation + grace period (+ tests in phase)
↓
Phase 10
Audit timeline UI
Surfaces the events already emitted in Phases 6 to 8.
Verify here that no update or delete path exists for audit events.
↓
Phase 11
Overdue alerts + cycle-scoped dismissal + nav count badge
(+ tests for alert reappearance in a new cycle)
↓
Phase 12
Search + filters + sorting + pagination (server-side)
↓
Phase 13
Bulk odometer CSV + per-row reporting (+ tests in phase)
↓
Phase 14
Service history CSV export
↓
Phase 15
Dashboard
↓
Phase 16
Seed data + test hardening + UI polish + error and loading states
↓
Phase 17
Final verification against all ten goals
Redeploy, walk the Success Metric checklist on the live URL,
hand the user the final documentation drafts.

---

# Coding Rules for Claude

When implementing features:

1. First understand the existing architecture.
2. Do not rewrite working code unnecessarily.
3. Prefer small incremental changes.
4. Before modifying the database schema, inspect existing models and migrations.
5. Before adding an API endpoint, check whether an equivalent endpoint exists.
6. Keep route handlers thin.
7. Put business rules in service-layer functions.
8. Put database access in repositories where appropriate.
9. Use Pydantic schemas for API input/output.
10. Use TypeScript types on the frontend.
11. Validate input on both frontend and backend.
12. Never rely on frontend validation for security.
13. Add tests for important business rules.
14. Do not introduce unnecessary libraries.
15. Do not create mock implementations unless explicitly requested.
16. Do not remove existing functionality without a clear reason.
17. Preserve existing coding conventions.
18. Explain significant architectural changes.
19. Prefer readable code over clever code.
20. Keep implementation explainable in an interview.

---

# Before Implementing Any Feature

Claude should first determine:

1. Which requirement does this feature satisfy?
2. Which database entities are involved?
3. Which API endpoints are required?
4. Which user roles can access it?
5. What business rules apply?
6. What validations are required?
7. What audit events should be generated?
8. What tests are required?
9. Does this affect existing functionality?
10. Does the documentation need to be updated?

Do not immediately start coding without understanding these dependencies.

---

# Definition of Done

A feature is not complete merely because the UI works.

A feature is complete when:

* Backend implementation exists.
* Database changes are correct.
* Authorization is enforced.
* Business rules are enforced.
* Frontend UI is implemented.
* Loading states exist.
* Error states exist.
* Tests cover important behavior.
* Audit events are created where required.
* Documentation is updated where appropriate.
* The feature works against real PostgreSQL data.
* No secrets are committed.
* The implementation is understandable and explainable.

---

# Final Principle

Build a reliable fleet maintenance system first.

Do not optimize for:

* Number of components
* Number of libraries
* Visual complexity
* Lines of code
* AI-generated code volume

Optimize for:

* Correct business rules
* Secure authorization
* Data integrity
* Auditability
* Maintainability
* Clear architecture
* Good user experience
* Testability
* Explainability

The application should demonstrate engineering judgment,
not just the ability to generate a working interface.