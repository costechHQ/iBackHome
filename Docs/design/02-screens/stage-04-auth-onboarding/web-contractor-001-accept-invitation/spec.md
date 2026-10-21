---
id: WEB-CONTRACTOR-001
title: "Accept an invitation"
stage: 4
surface: web
role: contractor
priority: P0
fr: ["FR-03", "FR-01"]
route: "/invite/:token"
suggested_target: "web/src/features/auth/"
api: ["POST /auth/otp/request", "POST /auth/otp/verify"]
links_to: ["WEB-CONTRACTOR-002"]
states: ["default", "2-invitation-with-project-preview", "3-confirm-its-you", "4-joined", "5-declined", "6-expired-or-already-used", "7-signed-in-with-another-number", "invitation-contractor-at-a-computer", "loading", "error"]
inventory_refs: ["AU-05"]
missing_endpoints: ["MX-02"]
source_boards: ["Auth-Invite.dc.html"]
---

# WEB-CONTRACTOR-001 · Accept an invitation

## 1. Purpose

Let an invited contractor preview the project, confirm it is them with a code, and accept or decline. Covers expired, used and wrong-number cases.

From the approved board (`Auth-Invite.dc.html`): "Chioma invites Engr. Obi by phone. He gets a WhatsApp link, sees what he's joining, confirms with a code sent to the invited number, and lands in contractor onboarding. Mostly on a phone, so mobile first."

Stage 1 inventory: AU-05. Priority P0 · FRs FR-03, FR-01.

## 2. Layout and components used

Frames in `screen.html` (one per designed state):

| # | State | Variant | Size | Screenshot |
|---|---|---|---|---|
| 1 | 2 · Invitation with project preview | mobile | 390×844 | [mobile.png](mobile.png) |
| 2 | 3 · Confirm it's you | mobile | 390×844 | [mobile-02-3-confirm-its-you.png](mobile-02-3-confirm-its-you.png) |
| 3 | 4 · Joined | mobile | 390×844 | [mobile-03-4-joined.png](mobile-03-4-joined.png) |
| 4 | 5 · Declined | mobile | 390×380 | [mobile-04-5-declined.png](mobile-04-5-declined.png) |
| 5 | 6 · Expired or already used | mobile | 390×380 | [mobile-05-6-expired-or-already-used.png](mobile-05-6-expired-or-already-used.png) |
| 6 | 7 · Signed in with another number | mobile | 390×380 | [mobile-06-7-signed-in-with-another-number.png](mobile-06-7-signed-in-with-another-number.png) |
| 7 | Invitation (contractor at a computer) | desktop | 1280×760 | [desktop.png](desktop.png) |

Components (see [components.md](../../../01-design-system/components.md)): Buttons, Status chip, Dialog and alert dialog, Card.

## 3. Data shown

| UI field | API field (Spec) |
|---|---|
| Project title | projects.title (GET /projects/{id}) |
| Address | projects.address |
| Project status chip | projects.status |
| Budget | projects.budget_minor + projects.currency |
| Inviting client | projects.client -> users.full_name, country |

Sample values are in [fixtures.json](fixtures.json) (PLACEHOLDER data).

## 4. Interactions and navigation

Actions on the design: "Accept and continue", "Decline", "Send code", "Set up my profile", "Close", "Go to sign in", "Sign out and switch".

API calls (all under `/api/v1`, bearer JWT, writes send `Idempotency-Key`):

- `POST /auth/otp/request`
- `POST /auth/otp/verify`

Needs data the Spec does not provide (use a mock adapter with the sample in fixtures.json and log it):

- MX-02: Project invitations

Navigates to: WEB-CONTRACTOR-002.

## 5. States and error cases

Designed states: 2 · Invitation with project preview; 3 · Confirm it's you; 4 · Joined; 5 · Declined; 6 · Expired or already used; 7 · Signed in with another number; Invitation (contractor at a computer).

Loading, empty, offline, 403/404/409/500 and session-expired states use the shared patterns in WEB-CLIENT-024 (system states) and the empty-state screens.

## 6. Business rules the UI must enforce

- Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- Role and project membership are checked on every request; each role sees only its own screens.

## 7. Responsive and accessibility notes

- Designed variants: mobile (6), desktop (1).
- Visible focus ring (2px accent) on every interactive element; keyboard reachable in visual order.
- Text contrast 4.5:1 minimum (body #3A4354 and muted #5F6878 pass on white and mist); non-text 3:1.
- Use real buttons, links and labelled inputs; icons that carry meaning have text or aria-label.
- Touch targets at least 44×44px on mobile web.

## 8. Open questions

- Invitations last 7 days and resends are limited to one per 10 minutes (Stage 1 assumption, confirmed).
- PLACEHOLDER: names, phone numbers, amounts, rates, dates and IDs shown are sample data, not production copy.
- MX-02: View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor".
