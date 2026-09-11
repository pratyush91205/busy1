# Schema

PostgreSQL 17. Everything below exists as of migration `0002_domain_schema`.

Conventions across all tables: `BIGINT` identity primary keys, `TIMESTAMPTZ` for
every timestamp, `created_at` and `updated_at` on tables that change,
`created_at` alone on append-only ones. Every foreign key is `ON DELETE
RESTRICT`, because nothing here is ever hard deleted.

## Tables

### users

| column | type | notes |
|---|---|---|
| id | bigint identity | pk |
| email | text | unique |
| full_name | text | not null |
| password_hash | text | never serialised, no API schema exposes it |
| role | varchar(20) | check in (`fleet_manager`, `technician`) |
| created_at, updated_at | timestamptz | |

### vehicles

| column | type | notes |
|---|---|---|
| id | bigint identity | pk |
| registration_number | text | unique |
| make, model | text | |
| current_odometer | integer | check `>= 0`, holds the latest reading |
| service_date_interval | integer | check `> 0`, in days (column comment) |
| service_mileage_interval | integer | check `> 0`, in miles (column comment) |
| is_archived | boolean | default false, indexed |
| created_at, updated_at | timestamptz | |

### service_records

| column | type | notes |
|---|---|---|
| id | bigint identity | pk |
| vehicle_id | bigint | fk to vehicles, indexed |
| cycle_number | integer | check `> 0`, unique together with vehicle_id |
| description | text | check `char_length(btrim(description)) > 0` |
| status | varchar(20) | check in (`due`, `booked`, `in_service`, `completed`) |
| scheduled_date | date | null until booked, indexed |
| due_since | timestamptz | when this cycle became due, indexed |
| completed_at | timestamptz | null until completed |
| completion_odometer | integer | check null or `>= 0` |
| created_at, updated_at | timestamptz | updated_at indexed for sorting |

One row is one service cycle for one vehicle. `cycle_number` counts from 1 per
vehicle, and `(vehicle_id, cycle_number)` is unique.

### service_technicians

Join table. Composite primary key `(service_id, technician_id)`, plus
`assigned_at`. There is one extra index, on `technician_id`. I did not add one
on `service_id` because that is already the leading column of the primary key
index, so a second one would never be chosen.

### service_notes

`id`, `service_id` (fk, indexed), `author_id` (fk), `content` (check not blank),
`created_at`. No `updated_at`, because notes are append-only.

### audit_events

`id`, `service_id` (fk), `actor_id` (fk, nullable), `event_type` (check against
five values), `old_value`, `new_value`, `event_metadata` (jsonb), `created_at`.

`actor_id` is nullable on purpose: a record becoming due happens on a clock, not
because a person did something, and writing a fake actor for that would be worse
than recording that the system acted. The index is composite on `(service_id,
created_at)`, since reading one service's timeline in order is the only query
this table ever gets.

### overdue_alert_dismissals

`id`, `service_id` (fk, unique), `dismissed_by` (fk), `dismissed_at`.

## Relationships

One-to-many:

- vehicles to service_records
- service_records to service_notes
- service_records to audit_events
- users to service_notes as author, to audit_events as actor, and to dismissals

Many-to-many:

- service_records to users (as technicians), through `service_technicians`

One-to-at-most-one:

- service_records to overdue_alert_dismissals, held by the unique constraint on
  `service_id`

## Database constraints versus application constraints

The line I drew is this. If violating it would corrupt the data model, the
database enforces it. If enforcing it needs context about the request, the
service layer does.

The database enforces uniqueness (registration number, email, one dismissal per
cycle, one assignment per technician per record), value ranges (odometer not
negative, intervals positive, text not blank), the closed set of enum values,
referential integrity, and audit immutability.

The service layer enforces the rest:

- An odometer reading may not be lower than the current one. That needs the
  existing row to compare against, and the bulk CSV upload has to turn it into a
  per-row rejection message rather than an exception.
- Lifecycle transitions. `Due -> Booked` is legal, `Due -> Completed` is not. A
  check constraint sees one row at a time and cannot see what the row used to
  be, so this belongs in code.
- Authorization. The database has no idea who is asking.

One rule I deliberately pushed down into the database rather than keeping in
code: audit immutability. "Nothing in this timeline can be edited or deleted,
including by fleet managers" felt too important to rest on the absence of an
endpoint, so `audit_events` has `BEFORE UPDATE` and `BEFORE DELETE` row triggers
that raise. That holds through the ORM and through a psql session, and there is
a test that proves both. Row triggers do not fire on `TRUNCATE`, which is how
the test suite still cleans up between cases.

The four status values live in a check constraint rather than a native
PostgreSQL enum type. Adding a value later is then a one-line migration instead
of an `ALTER TYPE`, and the values stay readable in psql.

## What I deliberately denormalised

Nothing so far. Two things look like omissions and are actually choices:

**No odometer history table.** `vehicles.current_odometer` is the latest
reading, and the odometer needed for service cycle maths is the completion
odometer already stored on the completed service record. A separate history
table would add a migration, a repository and a join, and the brief asks for
neither. The cost is real though: if a wrong but higher reading gets in, there
is no trail back to the CSV row that introduced it.

**No stored overdue alerts.** Overdue is computed from `status = 'due'` and
`due_since` against the grace period. If alert rows existed, something would
have to create them, and then the row and the computation could disagree about
whether a vehicle is overdue.

`due_since` might look like denormalised data, but it is not derivable. It
records when a cycle became due. Recomputing it from the intervals would mean
that editing a vehicle's intervals silently moves an overdue clock that was
already running.

## What breaks first at 100x

With a few dozen vehicles this database is small. At a few thousand vehicles and
several hundred thousand service records, in the order I expect them to hurt:

1. The service list search. Text search over `description` is an `ILIKE` scan
   today. This is the first thing to go, and the fix is a GIN index on a
   `tsvector`, or `pg_trgm` if substring matching matters.
2. The overdue query. `status = 'due' AND due_since < now() - interval` uses two
   separate single-column indexes. A composite `(status, due_since)` index would
   serve it directly. I left it out because at this size it would be guesswork.
3. Dashboard aggregates. Counting completions per week over eight weeks scans
   the completed records. It stays cheap much longer than the list query, and
   when it stops being cheap the answer is a summary table updated on
   completion, not a cache.
4. `audit_events` size. It is the only table that grows forever and is never
   pruned, which is the point of it. Partitioning by month is the eventual
   answer.
