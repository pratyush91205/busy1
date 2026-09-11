---
description: Create a feature specification for the Fleet Maintenance System
argument-hint: <number> <feature-slug> e.g. 04 service-lifecycle
allowed-tools: Read, Write, Glob, Grep, Bash(git:*)
---

You are writing an implementation spec for the Fleet Maintenance System.

User input: $ARGUMENTS

Read CLAUDE.md first. It holds the global rules: stack, architecture, business
rules, phase order, protected files. This command specs ONE feature.

# What a spec is for

A spec records the decisions needed to build one feature that are NOT already
in CLAUDE.md.

Never restate CLAUDE.md. No sections on the tech stack, coding style, general
security, error-handling conventions or transaction policy. Those are global and
already decided. A spec that repeats them is noise, and noise costs hours against
a 12-hour budget.

Write it so implementation can start from it without further questions.

Target: under 200 lines. Longer than that means it is restating CLAUDE.md.

# Hard rules

* Protected Files: never plan to write README.md, SUBMISSION.md, or anything in
  docs/. If the feature produces documentation content, list it as a draft to
  hand to the user.
* All work happens on `main`. Never create a feature branch.
* Scope is the ten required goals. Do not spec stretch features unless asked.
* Do not invent filenames. Inspect the repository first.

# Step 1 - Resolve root and arguments

The project root is the directory containing CLAUDE.md. All paths below are
relative to it.

Parse $ARGUMENTS into:

* feature_number - zero-padded (4 becomes 04)
* feature_title - human readable (Service Lifecycle)
* feature_slug - kebab-case (service-lifecycle)

# Step 2 - Research before writing

Read CLAUDE.md, then inspect what already exists with Glob and Grep:

* apps/api/app/ - models, schemas, services, repositories, api
* apps/api/migrations/, apps/api/tests/
* apps/web/app/, apps/web/components/
* .claude/specs/ - existing specs and what they already cover

Establish the feature's current state: not started, partial, or done.

If it is already fully implemented, STOP and say so rather than writing a spec.
If partial, the spec must say what exists and what is missing.

# Step 3 - Locate the feature in the plan

State:

* which of the ten required goals it satisfies
* which phase it is in the CLAUDE.md Development Order
* which phases must be complete first

If its dependencies are not built yet, say so and recommend those first.

# Step 4 - Write the spec

Use exactly these sections. If one genuinely does not apply, keep the heading
and write "None."

---

# Spec NN - <feature_title>

## Overview

Three or four sentences: what it does, why, which goal, which phase.

## Depends on

Features that must exist first, and why. Or "None."

## Current state

Not started / partial / done. If partial, what exists and what is missing.

## Data model

New tables, new columns, types, foreign keys, unique and check constraints,
indexes, and the Alembic migration required. Or "No schema changes."

## Business rules

Numbered list of what the SERVER enforces for this feature. Each rule states its
condition and its rejection, including the HTTP status. Use real values.

Good: "A reading lower than vehicles.current_odometer is rejected 422, with the
existing and submitted values in the message."

Bad: "Validate the odometer."

## Permissions

Fleet Manager - allowed actions.
Technician - allowed actions.
Forbidden - who is blocked from what, and the status returned.

Every line here is enforced server-side. Hiding a button is not a permission.

## API

One row per endpoint: method, route, auth, authorization, request body, response
body, error codes. Keep it tight.

## Audit events

Event types emitted, with old value, new value, actor, and when each fires.
Emitted in the same transaction as the mutation. Or "No audit events."

## Frontend

Pages touched, components new or changed, and the required loading, error and
empty states. Skip decorative detail.

## Tests

Specific cases, each traceable to a business rule above. Cover the happy path,
every rejection, and every authorization boundary. Pytest, written in the same
phase as the code.

## Definition of done

A checklist of verifiable items specific to THIS feature - things a reviewer
could actually check. Not the generic CLAUDE.md checklist.

## Risks and open questions

Anything genuinely uncertain, and any decision the user still needs to make.
Or "None."

---

# Step 5 - Save

Write to:

.claude/specs/<feature_number>-<feature_slug>.md

# Step 6 - Commit

If the project root is a git repository:

git add .claude/specs/<file>
git commit -m "docs: add <feature_title> spec"

Commit only the spec file. Do not stage unrelated work. Do not push.

If it is not a git repository yet, say so and skip the commit. Do not run
git pull, and do not stop because the working tree is dirty - uncommitted work
in progress is normal and is not a reason to refuse to write a spec.

# Step 7 - Report

Print:

Spec:     .claude/specs/NN-slug.md
Goal:     <which of the ten>
Phase:    <CLAUDE.md phase>
Depends:  <list or none>
Schema:   yes/no
API:      <count> endpoints
Audit:    yes/no

Then list anything the user must decide before implementation starts.

Do not start implementing. The spec gets reviewed first.
