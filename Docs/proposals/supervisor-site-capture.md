# Proposal: on-site boundary capture by the supervisor

Status: **proposed, not built**. Needs a decision from Christopher before any code. It adds a route, a table and
a rule to the spec, and CLAUDE.md says to propose those first. Owners: projects/sites (Christopher), the
mobile capture screen (mobile owner), evidence checks (Abigail).

## Problem

Today the client draws the pin and boundary on a map from abroad (`PUT /projects/{id}/site`). For a rural plot
that is the weakest step in the evidence chain:

1. The client may not be able to find the plot. In a village missing from OpenStreetMap the tiles show bare land
   with nothing to line up against. (The satellite layer and the address-area start in #95–#97 help, but they
   are still a guess from a screen.)
2. Every evidence check (spec, "Server checks", geofence row) trusts that polygon. A boundary drawn in the
   wrong place makes honest photos `rejected` and, worse, makes photos from the wrong place `accepted`.
3. Phone GPS is off by 5–20 m, more under trees. A tight polygon around a small plot plus the 25 m buffer can
   still reject honest photos.
4. Nothing checks the pin is in the right village. The web now warns above 50 km from the address, but that is
   only a warning.

The person who is actually standing on the plot is the assigned supervisor. We should let them supply the
ground truth, without letting them quietly move the fence the evidence is judged against.

## What we are not changing

- The server still decides; the device only warns (evidence rule).
- The 25 m buffer and the check order in the spec stay as they are (see "Small plots" for the one open question).
- Site lock: the client can change the site only in `draft` / `boq_review`; ops at any time; every change
  audited (spec, project rules). A supervisor never writes to `sites` directly.

## Proposal: propose → confirm

The supervisor **proposes** a measured boundary; the **client or ops confirm** it. Only confirmation changes
`sites`. This keeps a collusive or mistaken supervisor from moving the fence unilaterally, and it fits the lock
rules because confirmation goes through the same service function that already enforces them.

### Flow

1. The supervisor is assigned to the project (`projects.set_supervisor`).
2. In the supervisor app, **Site survey** (needs GPS, works offline): walk the corners of the plot and tap
   *Add corner* at each one (at least 3). For each corner the app records latitude, longitude and the GPS
   accuracy reported by the phone, and it can average several seconds of fixes per corner to reduce drift.
   The app also records one centre pin (the site pin).
3. The app shows an on-device warning if any corner accuracy is worse than 25 m (the supervisor can retry);
   it can still submit. The server decides.
4. The app submits the survey (sync queue if offline, keeping the original capture time).
5. The client (web) and ops see **"Supervisor survey waiting"** on the site screen, with the proposed polygon
   drawn over the current one on the satellite layer and the largest corner accuracy. They **Accept** or
   **Reject** (rejection needs a note).
6. Accept replaces the site through the existing `set_site` logic (pin inside polygon rule, site lock rule,
   audit entry). Reject keeps the current site and tells the supervisor why.

### Why not let the supervisor write the site directly

The geofence is the reference for the core promise. If the person whose photos are judged against it could also
edit it, the check would prove nothing. Proposal-then-confirm keeps two different parties in the loop (the
person who measures, the person who owns the money or ops).

## Proposed API (new; not in the spec today)

| Method | Path | Who | What |
| --- | --- | --- | --- |
| POST | `/projects/{id}/site/surveys` | assigned supervisor | Submit a survey: pin, corners with per-corner accuracy, `captured_at`, `device_id` |
| GET | `/projects/{id}/site/surveys` | members, ops | List surveys (latest first) with status |
| POST | `/projects/{id}/site/surveys/{survey_id}/decision` | client, ops | `accept` or `reject` (reject needs `notes`) |

All three accept `Idempotency-Key` and use the usual error shape. Call them only through `projects/service.py`.

Errors: 403 `not_project_supervisor`; 409 `survey_not_pending` (already decided); 409 `site_locked` on accept
by a client after the lock (ops can still accept); 422 `pin_outside_geofence` (reused from the site rule);
422 `survey_too_few_corners`.

## Proposed table (new)

`site_surveys`: `id`, `project_id` → projects, `supervisor_id` → users, `device_id` → devices, `pin` POINT
4326, `geofence` POLYGON 4326, `max_corner_accuracy_m` NUMERIC, `captured_at`, `status`
(`pending` | `accepted` | `rejected` | `superseded`), `decided_by`, `decided_at`, `decision_notes`, plus the
usual timestamps. GiST index on `geofence` is not needed (nothing queries by it).

## Proposed status machine (new)

| From | To | Who | Condition |
| --- | --- | --- | --- |
| (new) | `pending` | assigned supervisor | At least 3 corners, polygon valid, pin inside |
| `pending` | `accepted` | client, ops | Site rules pass (lock, pin inside); replaces `sites` row |
| `pending` | `rejected` | client, ops | Notes required |
| `pending` | `superseded` | system | A newer survey is submitted |

Invalid transition: HTTP 409. Every transition writes an audit entry (`audit.record`), including the
before/after site geometry on accept.

## Integrity: sign the survey like evidence

A survey carries claims about places, so it should get the same protection as a photo: sign the survey payload
with the device key (ECDSA P-256, registered device) and have the server verify it through
`evidence/signing.verify_signature()` (via evidence's `service.py`), check the device belongs to the supervisor,
and check `captured_at` is within the clock window. No file is involved, so no hash or pHash check. This stops
a survey being typed in from a desk with made-up coordinates and ties it to a registered phone.

## Who needs to do what

| Area | Work |
| --- | --- |
| Spec | Add the three routes, the `site_surveys` table, the status table, the permission-matrix row |
| Backend (projects) | Model, migration (chain after the head on `main`), service functions, router, tests |
| Backend (evidence) | Expose a signing check for a survey payload (no new rule) |
| Mobile | Site survey screen with per-corner averaging and offline sync |
| Web | "Survey waiting" panel on `/projects/{id}/site` and the ops project page; accept/reject buttons |
| Notifications | Message the client and ops when a survey is waiting; the supervisor when it is decided |

Tests that must exist (permissions and state changes, per CLAUDE.md): only the assigned supervisor can submit;
a client cannot accept after the lock but ops can; accept updates `sites` and writes an audit row; a second
survey supersedes the first; an unsigned or foreign-device survey is refused; replaying an `Idempotency-Key`
does not create two surveys.

## Open questions for Christopher

1. **Who may accept:** client and ops, or ops only after the lock? (This proposal: client while the site is
   unlocked, ops always.)
2. **After the BoQ is approved** the site is locked. Should a supervisor survey be allowed then (ops accepts) so
   a wrong fence can be fixed once the real supervisor arrives? This proposal says yes, because the supervisor
   is often assigned after approval.
3. **Small plots and drift (separate from this proposal):** keep the flat 25 m buffer, or widen it for plots
   under a size? That is an evidence rule in the spec and Abigail's checks, so it should be its own decision.
   One option is to compute the buffer as `max(25 m, survey max corner accuracy)`, but that makes it easier to
   pass the geofence, so it needs a ceiling.
4. **First visit:** should the supervisor's first spot check be tied to a completed survey, so a site is never
   left on an unverified client-drawn fence?

## Rejected alternatives

- **Client only, with better maps:** done as far as web can go (#95–#97); still a guess from a screen.
- **Client captures the boundary by standing on the plot:** possible for clients in Nigeria, useless for the
  main user (abroad). The "Use my current location" pin already covers that case.
- **Supervisor writes the site directly:** removes the second party; see above.
