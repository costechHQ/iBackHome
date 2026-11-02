# Proposal: the backend routes the Android app is waiting for

Status: **approved 2026-11-02 (D1 to D5 as recommended); building in the order of D5**. Each item still ships in its own PR with its owner as reviewer. The items add a route, a
column or a table that is not in `Docs/spec.md`, and CLAUDE.md says to propose those first. The gaps come from
the design package (`Docs/design/04-api-mapping/missing-endpoints.md`, ids MX-xx) and from what the mobile
work found missing. Every claim below was checked against `main` on 2026-11-02.

## Why now

The app is built against the design, but eight things still show sample data, a placeholder or nothing. None
can be finished in the app alone, and the design package says not to invent endpoints:

| # | Need | Design id | Today in the app | Folder owner |
|---|---|---|---|---|
| P1 | List my devices | MX-12 | Settings says a list of old phones "isn't in the app yet" | Abigail (`evidence/`) |
| P2 | Push tokens and notification preferences | MX-01 (rest) | No push at all; `notifications/service.py:65` returns `None` ("device push tokens are not stored yet") | Lilian (`notifications/`), Christopher (`users/`) |
| P3 | Notification feed | MX-11 | Alerts tab shows labelled sample data, debug builds only | Lilian |
| P4 | Material order reads | MX-05 | Orders tab shows labelled sample data, debug builds only | Abigail (`suppliers/`) |
| P5 | Party names and contact on a project | MX-26 | No contractor name or Call button; people are shown by role | Christopher (`projects/`) |
| P6 | Edit a report draft before review | MX-13 | Review-only; `POST /reports/{id}/review` takes no body | James (`reports/`) |
| P7 | Checklist templates | design G-10 | Four generic placeholder items for every milestone (`defaultChecklist`) | Lilian (`milestones/`), James (`seed.py`) |
| P8 | Supervisor NIN | design AND-SUPERVISOR-001 step 3 | Not collected; only an ops-set `nin_verified` flag exists | James (`supervision/`) |

Rules that apply to all of them (CLAUDE.md): features talk through each other's `service.py`; every write
accepts `Idempotency-Key`; state changes go through the feature's `service.py` and write an audit entry; errors
use the one error shape; lists use `?cursor=&limit=`; each item ships with tests (permissions, the happy path,
and the 403/404/409 cases).

## P1. List my devices (MX-12)

- `GET /devices`: the signed-in user's own devices, newest first. Roles: supervisor, contractor.
- Response: the existing `DeviceOut` without `public_key` (the app doesn't need it): `id`, `device_id`,
  `registered_at`, `revoked_at`. The app compares `device_id` with its own key to mark "this phone".
- Use: Settings lists old phones with a Revoke button that calls the existing `POST /devices/{id}/revoke`.
- Spec: one row in the API table. No migration.
- Tests: another user's devices never appear; revoked devices are listed with `revoked_at`.

## P2. Push tokens and notification preferences

Two small pieces; push can't work without both.

1. **Token registration.** `POST /me/push-tokens` `{device_pk, token}` (upsert by `device_pk`) and
   `DELETE /me/push-tokens/{device_pk}` (sign-out and revoke). New table `push_tokens` (user, device,
   token, created, updated). `notifications/service.py:65` then returns the user's tokens, which the existing
   `FcmPushAdapter` already sends to. Settings already has `FCM_PROJECT_ID` and `FCM_SERVICE_ACCOUNT_JSON`.
2. **Preferences.** `GET /me/notification-preferences` and `PUT /me/notification-preferences`
   `{push_enabled: bool}` (channel order and quiet hours stay out of scope). Stored on the user. Spot-check SMS
   is not a preference: it stays on (spec and design say it cannot be turned off).

- Needs from Christopher: the Firebase project and its credentials (never in the repo; `.env.example` lists the
  variable names only).
- Tests: a token is stored once per device and removed on revoke; with `push_enabled = false` the push channel is
  skipped and the fallback order runs; another user's token cannot be removed.

## P3. Notification feed (MX-11)

- `GET /me/notifications?cursor=&limit=` and `POST /me/notifications/{id}/read`.
- Needs a `read_at` column on `notifications` (migration chained after the current head). Login codes are never
  returned: they are stored with no user, and the feed filters on `user_id`.
- Tests: the feed holds only the caller's rows, newest first; marking read is idempotent; another user's id is 404.

## P4. Material order reads (MX-05)

- `GET /projects/{id}/orders` (project members and ops) and `GET /orders/{id}`.
- Reuses the existing order model and the `require_project_member` check. No writes, no migration.
- Out of scope here: put on hold and cancel (also in MX-05); supplier-side lists.
- Tests: members see their project's orders; a non-member gets 403 `not_project_member`.

## P5. Party names and contact on a project (MX-26)

- `GET /projects/{id}` gains `contractor` and `supervisor` objects `{id, full_name, phone}` next to the existing
  ids, read through `users.get_user` (never a direct query).
- Privacy decision (D4): the phone is returned only to the project's own members and ops. Suspended accounts
  keep their name but show no phone. The app's Call button and the client's People card both need this.
- Tests: a member sees names and phones; a non-member gets 403 as today; no phone for a suspended user.

## P6. Edit a report draft (MX-13)

- Today the report body is AI-written and the supervisor can only approve it. The rule "money figures come from
  the ledger, never the model" means free editing of the body could change a figure.
- **Recommended (D1):** `PATCH /reports/{id}` `{supervisor_note: str, max 2000}` on a `draft` only, by the
  assigned supervisor or ops. The AI body stays untouched; the note is stored in a new column, shown under the
  body labelled with the supervisor's name, and sent with the report. Audit entry with before and after.
- Alternative: allow `body_md` edits and re-check the money lines against the ledger before saving. More power,
  more risk, and the checker is new code in a money-adjacent path.
- Tests: only the assigned supervisor or ops; only while `draft`; a sent report is 409 `report_locked`.

## P7. Checklist templates (design G-10)

- Today every milestone shows four generic items in the app. The verify route already takes a checklist
  (`ChecklistItem`: name, passed, evidence ids), and the spec says assigned milestones carry their checklists.
- **Recommended (D2):** a `checklist_templates` table (milestone name, ordered items) seeded by `seed.py` and
  copied into a new `milestones.checklist` (JSONB) column by `create_for_project()`, so editing a template later
  never changes a live milestone. `GET /projects/{id}/milestones` returns `checklist: [str]`; the app drops
  `defaultChecklist`. An ops screen to edit templates is a later web task.
- **Needs from the product owner:** the real items for foundation, blockwork to lintel, roofing, plastering and
  finishing. They must not be invented in code.
- Tests: a new project's milestones get the template items; changing a template doesn't change existing
  milestones; verify still requires every item to pass with evidence.

## P8. Supervisor NIN (design AND-SUPERVISOR-001, step 3)

- `PUT /supervisors/me/profile` accepts `nin` (11 digits, write-only). **Recommended (D3):** the server keeps
  only `nin_last4` and never stores or logs the full number (the design rule: only the last 4 digits are kept
  after the check). Ops still set the existing `nin_verified` after checking it; no outside provider.
- Migration adds `nin_last4`. The profile response returns `nin_last4`, never more.
- Tests: the full number is absent from the response, the database and the audit log; bad lengths are 422.

## Decisions needed

| # | Question | Recommended |
|---|---|---|
| D1 | Report editing: a supervisor note, or free edit of the body? | The note (P6) |
| D2 | Checklist items: seeded templates copied into each milestone, with ops editing later? | Yes (P7) |
| D3 | NIN: keep only the last 4 digits? | Yes (P8) |
| D4 | Contact: phones shown to the project's members and ops only? | Yes (P5) |
| D5 | Build order | P1, P5, P2 with P3 (push needs Firebase), P4, P6, P7, P8 |

## What the app does meanwhile

Nothing changes: no new mocks. Orders and alerts keep their labelled sample data in debug builds only, and the
checklist keeps the generic placeholder items. Each route lands in its own PR with its owner as reviewer, and the
app's matching change follows the same week. Money and evidence code is not touched by any item above.
