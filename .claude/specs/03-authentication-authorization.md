# Spec 03 - Authentication and Authorization

## Overview

Email and password sign-in, JWT-verified requests, and the two-role split that
every later endpoint depends on. This is goal 1 (accounts and roles) and Phase 4
of the CLAUDE.md Development Order. It delivers the reusable authorization
primitives - `get_current_user` and `require_role` - so that no later phase
invents its own check, and the Fleet Manager / Technician boundary is decided in
exactly one place.

## Depends on

Spec 02 (database schema), for `users.email`, `users.password_hash` and
`users.role`. Nothing in this spec can be tested before that migration runs.

Spec 01 supplies `Settings.jwt_secret`, which is already required at startup, so
a deployment cannot run with an unset signing key.

## Current state

Not started. `JWT_SECRET` is read and validated by `app/core/config.py:38`;
there is no `app/auth/`, no user model, no login route, and nothing in
`apps/web` that knows about a session.

## Data model

No new tables. `users` is created by spec 02 and is used as-is.

New dependencies in `apps/api/requirements.txt`: `pyjwt` for signing and
verification, `bcrypt` for hashing. PyJWT over python-jose because it is the
maintained, narrower library; bcrypt directly rather than through passlib, whose
bcrypt backend is a recurring source of version breakage.

## Business rules

1. `POST /auth/login` with an email that exists and a password whose bcrypt
   verification succeeds returns 200 with a signed JWT and the user's public
   fields.
2. A wrong password returns **401** with the single message
   `Incorrect email or password`. An unknown email returns **the identical
   401 and message** - distinguishing them tells an attacker which addresses are
   real. The unknown-email path still performs a dummy bcrypt verification so
   the two answers take comparable time.
3. A request to a protected route with no `Authorization` header returns **401**
   `Not authenticated`.
4. A token that is expired, unsigned, signed with a different key, or malformed
   returns **401** `Invalid or expired token`. The reason is logged, never
   returned.
5. A valid token whose `sub` no longer matches a user returns **401**, not 500.
6. A valid token whose role is not permitted for the route returns **403**
   `This action requires the fleet_manager role`. The role comes from the
   database on every request, never from a claim the client could edit.
7. Tokens expire 12 hours after issue (`AUTH_TOKEN_TTL_HOURS`, default 12).
   There is no refresh token; an expired token means logging in again.
8. No endpoint creates a user, and no endpoint accepts a `role` field from a
   client. Roles are set only by the seed script (see Frontend/Tests below).
9. `password_hash` never appears in any response body; the response schema has
   no such field.

## Permissions

**Fleet Manager** - log in; read own profile.

**Technician** - log in; read own profile.

**Forbidden** - everything else in this spec, because it adds no domain routes.
What this spec actually delivers is the enforcement mechanism the later specs
use: `require_role("fleet_manager")` as a route dependency, returning 403.

The token carries `sub` (user id), `role` and `exp`. The role in the token is a
convenience for logging only; every authorization decision re-reads the user
row, so a role changed in the database takes effect on the next request rather
than at the next login.

## API

| method | route | auth | authorization | request | response | errors |
|---|---|---|---|---|---|---|
| POST | `/auth/login` | none | none | `{email, password}` | `{access_token, token_type: "bearer", expires_at, user: {id, email, full_name, role}}` | 401 bad credentials, 422 malformed body |
| GET | `/auth/me` | bearer | any authenticated user | none | `{id, email, full_name, role}` | 401 missing/invalid/expired |

New files: `app/auth/passwords.py` (hash, verify), `app/auth/tokens.py` (encode,
decode), `app/services/auth_service.py` (authenticate), `app/repositories/user.py`
(get by email, get by id), `app/schemas/auth.py`, `app/api/routes/auth.py`.
`app/api/deps.py` gains `CurrentUser` and `require_role`.

## Audit events

None. `audit_events.service_id` is `NOT NULL` and there is no service record to
attach a login to, so logins are not audited. Successful and failed logins are
logged at INFO/WARNING with the email and no password material. If login
auditing is wanted later it needs its own table, not this one.

## Frontend

* `apps/web/app/login/page.tsx` - email and password form, React Hook Form with
  a Zod schema. States: submitting (button disabled, spinner), field-level
  validation errors, and a form-level error showing the API's 401 message.
* `apps/web/lib/auth.ts` + `apps/web/hooks/use-auth.ts` - store the token, read
  the current user via TanStack Query against `/auth/me`, expose `logout()`
  which clears the token and the query cache.
* `apps/web/lib/api-client.ts` - attach `Authorization: Bearer <token>` when a
  token exists; on a 401 clear the token and redirect to `/login`.
* `apps/web/app/(app)/layout.tsx` - authenticated shell that redirects to
  `/login` while no user is loaded, with a loading state so the page does not
  flash. This guard is convenience only; the server is the boundary.
* `apps/web/app/page.tsx` - redirects to `/dashboard` when signed in, `/login`
  otherwise. The API status card from spec 02 moves under the authenticated
  shell.

Token storage: `localStorage`, sent as a bearer header. Chosen over an
httpOnly cookie because the API and the frontend are on different origins, which
makes a cookie require `SameSite=None; Secure` plus credentialed CORS - more
moving parts to get wrong than the XSS exposure it removes. Worth a line in
`docs/decisions.md`.

## Tests

`apps/api/tests/test_auth.py`. Where a rule needs a protected route, the test
builds a throwaway FastAPI app with `require_role` attached - no
test-only endpoint is added to the application.

1. Valid credentials return 200, a decodable token whose `sub` is the user id,
   and no `password_hash` anywhere in the body. (rules 1, 9)
2. Wrong password returns 401 with `Incorrect email or password`. (rule 2)
3. Unknown email returns byte-identical status and body to case 2. (rule 2)
4. Protected route without a header returns 401. (rule 3)
5. Garbage token, token signed with a different secret, and a token with `exp`
   in the past each return 401. (rule 4)
6. Token for a deleted user returns 401, not 500. (rule 5)
7. `require_role("fleet_manager")` returns 403 for a technician and 200 for a
   manager. (rule 6)
8. A token whose `role` claim has been tampered to `fleet_manager` is still
   refused 403 for a technician - the role is re-read from the database.
   (rule 6)
9. `GET /auth/me` returns the signed-in user's public fields. (API)
10. `bcrypt` verification rejects a hash of a different password, and two hashes
    of the same password differ (salted). (rule 1)

Seeding for tests and for local use: `apps/api/scripts/create_user.py`, a CLI
taking email, full name, role and password. It is the only way a role is
assigned, which is what keeps rule 8 true. Phase 16's demo seed reuses it.

## Definition of done

- [ ] `POST /auth/login` returns a token for a seeded manager and a seeded
      technician, verified with curl against a real database.
- [ ] Wrong password and unknown email produce identical responses.
- [ ] `GET /auth/me` with that token returns the user; without it, 401.
- [ ] A technician's token is refused 403 by a `require_role("fleet_manager")`
      route, including when the token's own role claim says otherwise.
- [ ] No response body anywhere contains `password_hash`; grep the schemas.
- [ ] The signing key comes only from `Settings.jwt_secret`; no default or
      fallback secret exists in the code.
- [ ] `scripts/create_user.py` creates both roles and stores a bcrypt hash, with
      the password never logged.
- [ ] Login page works end to end against the local API: bad password shows the
      401 message, good password lands on the authenticated shell, logout
      returns to `/login`.
- [ ] All ten tests pass with no skips.
- [ ] Several commits, roughly: password hashing, token encode/decode, login
      endpoint, current-user and require-role dependencies, auth tests, seed
      script, login page, authenticated shell.
- [ ] `docs/decisions.md` and `docs/architecture.md` drafts handed over
      (protected files): token storage, no refresh token, no signup endpoint.

## Risks and open questions

1. **No signup endpoint is a deliberate omission.** The ten goals require
   sign-in, not user management, and an open registration endpoint that accepts
   a role would break the core authorization promise. Consequence: demo accounts
   must be seeded, and their credentials recorded in `SUBMISSION.md`. If the
   user wants managers to be able to create technicians in the UI, that is a
   separate feature and should be specced as one.
2. **No login rate limiting.** Out of scope against the budget, and pointless
   without shared state on a free tier. Name it in
   `docs/architecture.md` under what was deliberately not built rather than
   leaving a reviewer to assume it was missed.
3. **12 hour token, no refresh.** A demo session will not outlive it; a reviewer
   returning the next day will be logged out and should be told so. The
   alternative, refresh tokens, is a meaningful amount of work for no assessed
   goal.
4. **Technician visibility is enforced per-resource, not by role alone.**
   `require_role` cannot express "only records assigned to me". That filtering
   is owned by spec 05/06 and must not be forgotten there - a technician with a
   valid token must still be refused another technician's record.
