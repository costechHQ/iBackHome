# Package report

Stage 14 handoff package for iBackHome, generated 21 Oct 2026 from the approved Design canvas (Stages 1–13). Nothing was redesigned; this report records what was checked, what is missing and what is inconsistent.

## Summary

| Check | Result |
|---|---|
| Screens: inventory / manifest / folders | 98 / 98 / 98 · match |
| Designed states (frames) exported, each with a screenshot | 296 (from 79 approved boards) |
| FR-01 to FR-23 without a screen | none |
| Relative links checked / broken | 2593 / 0 |
| Screens missing spec, fixtures, html or screenshot | 0 |
| spec.md front matter that fails to parse or lacks a field | 0 |
| JSON files that fail to parse | 0 |
| screen.html frames identical to the approved board render (≤1% pixels differ) | 288 of 296; the other 8 differ only by 1px sub-pixel text rounding on long pages and sign-in cards |
| Network requests when opening screen.html offline | 0 |
| Secrets or real personal data found | none |

## 1. Screen counts

Inventory (`00-overview/screen-inventory.md`): 98. Manifest (`manifest.json`): 98. Folders under `02-screens/`: 98. All three lists contain the same IDs.

All 285 frames detected on the 79 approved screen boards from Stages 3–12 are included, plus 11 state cards found in the completeness sweep (10 sign-in states on `Auth-SignIn`, 1 invitation panel on `Auth-Invite`): **296 frames in total, none dropped**. The Stage 1 inventory had 98 rows; its mapping to package screens is at the end of the screen inventory.

Per stage: Stage 3: 9, Stage 4: 13, Stage 5: 5, Stage 6: 5, Stage 7: 10, Stage 8: 11, Stage 9: 9, Stage 10: 7, Stage 11: 11, Stage 12: 18. Per surface: android 24, email 1, mobile-web 2, web 67, whatsapp 4.

## 2. Requirements without a screen

None. Every FR from FR-01 to FR-23 maps to at least one screen (`00-overview/requirements-traceability.md`).

Partly server-side (screens show the result only): FR-07 signature verification, FR-08 geofence rejection, FR-10 pHash index, FR-18 weekly generation job, FR-20 5-minute delivery.

## 3. Broken links

None. 2593 relative links in README, CLAUDE.md, index.html, every spec.md, every screen.html, the flows, the API mapping and the build plan resolve inside the package.

## 4. Screens missing a spec, fixtures or screenshot

None.

Every screen folder has `screen.html`, `spec.md`, `fixtures.json` and one PNG per designed state. Screens with no API (public pages, message templates, shared states) have a `fixtures.json` that says so and points to the copy in `screen.html`.

## 5. Gaps and assumptions carried over

### From Stage 1 (all confirmed by Gabriel on 20 Oct 2026)

| ID | What was unclear | Assumption designed to | Affects |
|---|---|---|---|
| G-01 | Public site The PRD describes no marketing site, pricing page or public sign-up path. | Landing, How it works, Pricing with [PRICE] placeholders, Become a supervisor, Privacy and terms. One CTA: "Start a project" → sign in. | PUB-01–05 |
| G-02 | Role on first sign-in OTP sign-in has no role choice, and each user has exactly one role. | Anyone who signs up uninvited becomes a client. Contractor, supervisor and supplier roles come only from an invitation or from ops. | AU-01 · AU-04 |
| G-03 | How a contractor is invited "Create project, invite contractor" has no invite record, link, expiry, decline, or a case for a contractor who already has an account. | Invite by phone or email → WhatsApp or email link → code sign-in → joins the project. Client sees Invited / Joined, and can resend or replace. | CS-03 · NS-01 · AU-05 · CO-01 |
| G-04 | How a supervisor gets an account Vetting needs a supervisor account first, but nothing says how one is created. | Applying via Become a supervisor creates a supervisor account in vetting "pending"; ops can also invite. Unvetted supervisors see only their status. | PUB-04 · AU-07 · AU-08 · OP-02 |
| G-05 | How suppliers are added and verified No endpoint to create a supplier, verify one, or save its payout details. | Ops adds and verifies suppliers in the console and invites the owner. Payout details are entered by ops. | OP-15 · SU-04 · AU-05 |
| G-06 | What a supplier can do The API gives suppliers no actions: no accept, dispatch, delivery date or price updates. | Supplier portal is read-only: orders, site location and contact, delivery confirmation, payment status. Plus WhatsApp messages. | SU-01–05 |
| G-07 | One person, two roles A contractor who is also building for themselves, or a supervisor who also contracts. | Separate accounts per role; no role switcher in the MVP. | AU-01 · NS-07 |
| G-08 | Family or proxies on the client side Clients often have a relative on site, but only one client per project exists. | Out of scope. One client per project; relatives aren’t users. | CS-01 |
| G-09 | Which currency the BoQ is in BoQ lines carry a currency and the project has one, but contractors price in NGN while clients pay in GBP/USD/EUR. When is FX applied? | BoQ is priced in NGN. Client screens show an indicative conversion marked "estimate" until funding, when the rate is recorded and fixed. | CS-06 · CO-03 · CM-01 · CS-09 |
| G-10 | Verification checklist content The checklist is free JSON. No list of items per milestone, minimum evidence, or who defines it. | Ops keeps one template per milestone (Foundation, Blockwork to Lintel, Roofing, Plastering, Finishing) with required photo counts. Shown read-only to all parties. | SV-07 · CM-02 · CO-05 |
| G-11 | Funding rhythm and fees Can the client fund ahead, or only the next milestone? Fee amounts are not known. | Client funds one milestone at a time, prompted when the previous one is released; funding ahead is allowed. Fees shown as [ESCROW FEE] and [STRIPE FEE]. | CS-09 · CM-01 · CD-01 |
| G-12 | When a contractor can dispute Contractors may raise disputes, but the state machine only allows verified → disputed, raised by the client. | Contractor can dispute a supervisor rejection. It opens an ops case without changing the milestone state. | CO-08 · OP-08 |
| G-13 | What the client sees during a claim Not stated whether the client sees a claim before verification. | Yes, read-only: "Claimed — waiting for supervisor". No approve or dispute until verified. | CM-01 · CM-02 · CD-01 |
| G-29 | Two ops approvals Dispute resolution needs two ops approvals, but ops has no sub-roles and nothing describes the hand-off. | Any two different ops users. The first proposes an outcome with notes; the second confirms. Both appear in the audit log. | OP-08 · OP-01 |
| G-14 | Short or wrong delivery There is no partial-delivery or order-dispute path. | Supervisor records actual quantities; any difference creates an ops queue item and blocks payment until ops decides. | SV-13 · OP-01 · SU-03 |
| G-15 | Where order money comes from Suppliers are paid by an escrow release, but orders aren’t tied to a funded milestone. | Approving an order funds it separately through Stripe, held in escrow like a milestone. Needs engineering confirmation. | CM-07 · CM-06 · CS-09 |
| G-16 | Who picks the supplier Not stated whether the contractor or the client chooses. | Contractor chooses from verified suppliers; client sees the supplier and can decline with a reason. | CO-09 · CM-07 |
| G-17 | Fixing a wrong report draft Review is approve-only; there is no edit or reject. | Reviewer can approve or send back to ops with a note; ops can regenerate. No free-text editing of AI output. | SV-09 · OP-10 |
| G-18 | Report never reviewed No deadline or escalation, so the report never sends. | Ops alert if not reviewed by Saturday 12:00 WAT; ops can review instead. | OP-01 · OP-10 |
| G-19 | Client sees spot checks? Not specified whether or when the client sees spot-check results. | Client sees completed spot checks (date, supervisor, findings, evidence) in project history, never scheduled ones. | CD-04 · CD-01 |
| G-20 | What happens after a mismatch "Mismatches flagged", but there is no flag record or next step. | Ops reviews findings in the queue and can pause the project, open a dispute or request rework. | OP-01 · OP-08 · OP-06 |
| G-21 | Missed spot check No reschedule or no-show handling. | Ops reschedules with another rotated supervisor; missed visits stay visible in ops history. | OP-14 · SV-11 |
| G-22 | How precise a location the client sees Personal EXIF is stripped for clients, but showing raw coordinates isn’t addressed. | Client sees a pin on the site map, the geofence and GPS accuracy, not raw coordinates. Ops sees full metadata. | CD-03 · OP-07 |
| G-24 | Contractor captures They are checked like supervisor captures, but it’s unclear whether clients see them. | Clients see them, clearly labelled "Contractor upload — doesn’t count toward verification". | CD-02 · CO-06 · SV-07 |
| G-28 | Contractor payments view The ledger endpoint is client and ops only; the contractor payout rail is undecided (ADR 8). | Contractor sees a simple list of releases for their milestones in NGN with status. P1. | CO-12 |
| G-31 | Escrow partner identity The partner isn’t chosen; unknown whether clients must pass the partner’s own checks (KYC) before funding. | Generic "licensed escrow partner" copy, no partner logo, no KYC step in the MVP. Revisit when the partner signs. | CS-09 · PUB-02 · all money screens |
| G-25 | Notification gaps No preferences endpoint, no in-app inbox, and no events for "report ready to review" or material orders. | Settings screen for channel order (P1). Add supervisor push for report review and WhatsApp for order events. No in-app inbox. | NS-02–NS-07 · SV-09 |
| G-26 | Approve in under 3 taps from a message A WhatsApp link that lands on a sign-in screen breaks the 3-tap target. | Deep links open the milestone directly while the 30-day session lasts; if signed out, code sign-in then straight back. | NS-02 · CM-02 · CM-03 · AU-02 |
| G-27 | Language Not specified. | English only for the MVP. | All |
| G-30 | Paused and completed projects No description of what each role sees. | Paused: banner with the reason; claims, captures and approvals disabled. Completed: read-only, with reports and ledger kept. | CD-01 · CO-02 · SV-02 |

Superseded later (the later approved stage wins): G-05 (suppliers now enter their own payout details, Stage 4), G-06 (suppliers can update prices, Stage 10), G-15 (order money comes from the milestone escrow, Stage 13 list), G-17 (Stage 9 designs an "Edit the draft" step; see conflicts), G-25 (Stage 7 designs an in-app notifications screen; see conflicts).

### From Stage 13 (final list, accepted)


**Accounts and onboarding**

- Uninvited sign-ups become clients; contractors are invited by the client; suppliers by ops only; supervisors apply and wait for vetting.
- COREN and NIOB are both accepted. The CAC number is optional for contractors.
- Invitations last 7 days; codes last 5 minutes; “resend” unlocks after 30 s; rate limit of 10 minutes after too many codes.
- Sessions: client [12 hours], supervisor app [30 days], ops [8 hours] or [30 minutes] idle. Ops sign-in needs an SMS code plus a security key.

**Project setup and BoQ**

- The BoQ is priced in NGN; client-currency figures are estimates until each milestone is funded.
- Checklists come from ops templates per milestone type.
- Client, contractor and ops all approve the BoQ; a resubmitted version resets all approvals.
- The site boundary locks when the project starts; editing it needs a reason and a second ops approval.

**Evidence and supervision**

- Captures must upload within 72 hours of being taken, or they're rejected; the app warns at 48 hours (C-1, decided 2026-10-21).
- The camera stops below 100 MB of free storage. Unsent evidence is never deleted automatically.
- Contractor photos are location-stamped but never count toward verification.
- Near-duplicate flag at a distance of 10 or less out of 64.
- Supervisors rotate every two milestones, with at least [3 days'] notice; a declared relationship to a contractor permanently blocks assignment to that contractor's projects.
- Clients see spot checks only after ops closes them; the contractor never sees them.
- A supervisor visits within [3 working days] of a claim.

**Money**

- “Funded” only after the escrow partner confirms; alert after [30 minutes].
- Exchange rate is held for [15 minutes] at payment and recorded per transaction.
- Release confirmation alert after [1 hour]; failed releases retried 3 times.
- Fees: escrow release fee [X]%, card processing [£ FEE]; totals [£ TOTAL]. Pricing [PRICE] values to be set.
- Material orders are paid from the milestone's escrow after the supervisor confirms delivery, which reduces the contractor's release.
- Supplier payments wait while their milestone is under dispute.
- Changing a payout account needs a phone code and pauses payouts for [24 hours].
- Escrow partner name [LICENSED ESCROW PARTNER] and its reference format [partner ref] are still to be confirmed.

**Disputes**

- Clients dispute a verified milestone; contractors can dispute a supervisor's rejection.
- Release needs two different ops approvers; rework needs one.
- Target decision time [2 business days]. A dispute can't be withdrawn. Contractors can't reply inside a dispute; it goes through ops.
- Delivery shortfalls are decided by ops.

**Orders and price index**

- Suppliers see orders only after client approval. There's no “dispatched” step.
- Contractors type the supplier's price per line; only funded milestones can have orders; clients decline with a reason rather than “ask to revise”.
- Price changes over [10%] need an ops check; stale after 14 days.

**Reports, AI and notifications**

- Reports are drafted Friday 16:00 WAT and sent only after review. Ops reviews when a draft is more than [48 hours] late or the supervisor is part of a dispute.
- AI output is always labelled; money lines come from the ledger; AI tools are read-only except saving a draft.
- The WhatsApp assistant hands off to ops on complaints; ops replies within [2 business hours].
- Spot checks go by push and SMS (per spec), not WhatsApp. Quiet hours hold messages overnight except approvals.
- Model version [model version] is a placeholder.

**Settings and data**

- Only clients choose a currency (GBP, USD, EUR) and time zone; everyone else is NGN and WAT.
- Data download ready within [24 hours]; ledger, audit and evidence kept [7 years]; account deletion blocked while money is in escrow.
- Supervisors and contractors can revoke old devices; moving a supervisor's signing key goes through ops.

**Public site and legal (placeholders)**

- [REGISTERED COMPANY NAME], [OFFICE ADDRESS], [CONTACT EMAIL], [TRUST EMAIL], [LEGAL EMAIL], [DPO NAME], [DPO EMAIL], [WHATSAPP NUMBER], [OPENING HOURS], [RESPONSE TIME], [REGULATOR], [HOSTING LOCATION], [RETENTION PERIODS], [CANCELLATION TERMS], [STRIPE FEE], [ESCROW FEE], [₦ RATE] per supervisor visit.

### Assumptions added while packaging (Stage 14)

- Screen granularity: one package screen per approved board, split by surface and role where one board mixed them (98 screens). Each designed frame is a state of its screen.
- List responses use `{"items": [...], "next_cursor": null}`; the Spec only names `?cursor=&limit=`.
- Human-readable references (EV-, R-, P-, O-, D-, T-) are carried as `display_ref` in fixtures; the Spec has UUIDs only.
- OTP failure HTTP codes (wrong, expired, locked, rate-limited) are assumed in error-codes-to-ui.md; the Spec names only 502/503 codes for sending.
- `suggested_target` folders follow the Spec layout; folders the Spec lacks are marked "new folder; not in the Spec" (public site, settings, deliveries, reports and notifications on Android, orders on Android).
- Routes in specs are suggestions; the Spec defines no web routes or Flutter screen names.

## Conflicts and inconsistencies (recorded, not fixed)

| # | Where | Design says | Spec / earlier decision says | Recommendation |
|---|---|---|---|---|
| C-1 | AND-SUPERVISOR-007 (offline frame), AND-SUPERVISOR-014 (push), Stage 13 assumption list | Captures not uploaded within [48 hours] are rejected | Spec: 72 h upload window, app warns at 48 h | Decided 2026-10-21 (Gabriel): the Spec and backend win. 72 h is the hard limit, 48 h the warning. The copy in AND-SUPERVISOR-007 and AND-SUPERVISOR-014 `screen.html` now says 72 h; their PNGs still show the old 48 h text. |
| C-2 | WEB-OPS-005, Stage 13 assumption list | Near-duplicate flagged at distance 10 or less of 64 | Spec: Hamming distance ≤ 8 | Decide. Config value defaulting to 8; show the configured value. |
| C-3 | AND-SUPERVISOR-011 | Supervisor can "Edit the draft" before marking reviewed | Stage 1 G-17: no free-text editing of AI output; Spec has review only | Decide. If kept, needs MX-13 and the edit must keep the AI label and citations. |
| C-4 | WEB-CLIENT-020 | In-app notifications screen | Stage 1 G-25: no in-app inbox; Spec has no feed endpoint | Approved in Stage 7; needs MX-11. |
| C-5 | WEB-SUPPLIER-004 | Order "Payment on hold" state | material_orders.status has no "on hold" | Backend decision (MX-05). |
| C-6 | WEB-OPS-012 | User status "Deactivated" | users.status: active, suspended | Backend decision or drop the option. |
| C-7 | WEB-OPS-004 | Editing a locked boundary needs a reason and a second ops approval | Spec: ops can change the site any time; audited | Treat as UI policy until the backend supports it. |
| C-8 | X-Empty board (WEB-CLIENT-025, WEB-CONTRACTOR-011, WEB-SUPPLIER-009, WEB-OPS-014) | 6 empty-state buttons render with browser-default styling because their style rule is scoped to another board class | Design system: secondary button | Build them as secondary buttons. The screenshots show the board exactly as approved. |
| C-9 | Stage 5 funding success frame | "Funded" chip in info tone | Every other board: neutral | Use neutral (state-to-ui.md). |
| C-10 | WEB-CONTRACTOR-006 | Dispute "Under review" chip in bad tone | Evidence "Under review" is warn | Keep Disputed (bad) for disputes, warn for evidence. |
| C-11 | Stage 1 G-12 vs Spec | Contractor can dispute a supervisor rejection | Spec state machine only has verified → disputed | Decided 2026-10-21 (Gabriel): not built. Logged in 04-api-mapping/missing-endpoints.md (MX-25). |

### Where the backend differs from the designs (found while building; the backend wins)

| # | Where | Design says | Backend does | What the web app does |
|---|---|---|---|---|
| B-1 | WEB-PUBLIC-010 "Wrong code" | Shows "3 attempts left" | `invalid_code` (400) has no attempts-left count | Shows the designed wrong-code message without the count. |
| B-2 | error-codes-to-ui.md, OTP rows | Assumed codes and statuses | `invalid_code` 400, `otp_expired` 400, `too_many_attempts` 429, `rate_limited` 429 with `Retry-After`; refresh reuse is 401 `refresh_token_reused` | Maps the real codes; the rate-limit wait comes from `Retry-After`. |
| B-3 | state-to-ui.md Dispute, WEB-OPS-006 | Rework needs one ops approver | `POST /disputes/{id}/resolve` needs two different ops users for **both** outcomes, and the second must choose the same outcome (409 `second_approval_required` / `resolution_mismatch`) | The proposer sees "Waiting for 2nd approver"; another ops user can only confirm the proposed outcome. |
| B-4 | WEB-OPS-001, AND-SUPERVISOR-003, WEB-CLIENT-023 sign-out | Sign-out ends the session | No sign-out endpoint (MX-19) | Sign-out clears the web cookies; the refresh token stays valid on the server until it expires. |
| B-5 | 01-design-system/tokens.css | `@font-face` rules pointing at `../05-assets/fonts` | (web build) | The web copy drops them and loads the same files with `next/font/local`; `--ibh-font-sans` / `--ibh-font-mono` point at those fonts first. |
| B-6 | WEB-CLIENT-003 create project, WEB-CLIENT-005 BoQ | Budget in the client's currency (£ GBP); BoQ amounts with "≈ £" | The project currency is the BoQ's and the milestones' currency, and funding treats milestone amounts as naira | Projects are created in NGN and the budget is entered in naira; the client chooses GBP, USD or EUR when funding each milestone (W6b). The "≈ £" estimates need a rate, which the backend gives only for funding. |
| B-7 | WEB-CLIENT-018 weekly reports | "You only see reports after the supervisor has reviewed them" | `GET /projects/{id}/reports` returns every report to project members, drafts included | The web shows the client only reviewed and sent reports. **For James:** the backend should leave drafts out for clients too, so no other client (Flutter, the API) can show unreviewed AI text. |
| B-8 | WEB-PUBLIC-003 pricing, WEB-PUBLIC-001 FAQ | "Escrow release fee ([X]% of each milestone, charged when it's released)" | The one fee (`FUNDING_FEE_BPS`) is charged when the client funds a milestone, as its own line on the checkout | The public pages call it the "funding fee", taken when you fund a milestone and never from the contractor's payment (as W-33 does on the funding page). |

### Web build notes (decided with Gabriel; recorded as each stage builds)

| # | Where | What the designs show | What the web app does, and why |
|---|---|---|---|
| W-1 | Every top bar and the ops sidebar | Links to screens that aren't built yet | Each item is hidden until its screen exists (`web/src/common/layout/nav.ts`, flag `ready`), so nobody follows a link to a 404. The dev gallery shows them all for comparison. |
| W-2 | ClientTop, ConTop, WEB-CLIENT-024 | "Help", "Help centre", "Contact us" | Hidden until those pages exist (WEB-PUBLIC-007; no help centre is designed). |
| W-3 | ClientTop, ConTop | Notifications bell with a count | Hidden until WEB-CLIENT-020 and MX-11 exist. |
| W-4 | Ops sidebar and header | Global search; "session 3 h left" | Hidden: no search endpoint, and the backend has no ops session limit (the design's 8 h is a placeholder). The environment badge (LOCAL / STAGING / PRODUCTION) is shown, from `IBH_ENVIRONMENT`. |
| W-5 | WEB-CLIENT-024 session expired | "signed out after [12 hours]" | The bracketed placeholder is left out: "For your security, you were signed out." |
| W-6 | WEB-CLIENT-008 route `/` vs WEB-PUBLIC-001 route `/` | Both the client home and the public landing page are at `/` | **Open conflict.** The client home stays at `/projects` until decided: `/` must stay a static public page (ADR 0004), so it can't also be a signed-in dashboard. |
| W-7 | WEB-CONTRACTOR-003 | Contractor home at `/c` | Built at `/c` (W1a had `/c/projects`). |
| W-8 | Focus ring | Sheet: 2px white + 4px accent ring | The token stylesheet's own `:focus-visible` outline (2px accent, 2px offset; on-dark colour inside `.ibh-on-navy`) is the one indicator everywhere. It is unlayered, so it always wins over component classes. |
| W-9 | WEB-CLIENT-013/014/015 "People", "Verified by Ifeanyi Okafor" | Names of the contractor and supervisor | Named by role ("the contractor", "the supervisor"); the People card is hidden until MX-26. |
| W-10 | WEB-CLIENT-013 evidence checklist before verification | Rows from ops checklist templates ("Not captured") | No template endpoint (missing field "Checklist templates"): before verification the card lists the supervisor's captures for the milestone; after it, the supervisor's own checklist. |
| W-11 | WEB-CLIENT-010 filters | Date range filter | No date filter in `GET /projects/{id}/evidence`; left out. Cards show the short id where the design has a title (evidence has no title field). |
| W-12 | WEB-CLIENT-015 raise a dispute | "Evidence it's about" picker | `DisputeCreate` has only `reason`; the picker is left out and the chosen "What's wrong?" starts the reason. |
| W-13 | WEB-CLIENT-015 outcomes A and B, dispute timeline | Resolved dispute pages | Need MX-10 (no dispute read): only "Release paused" is built. |
| W-14 | WEB-CLIENT-017 ledger | Nightly reconciliation sentence, "[£ FEE]", "Paid into bank accounts" card | No endpoint for the reconcile result; the fee placeholder is dropped; the payouts card and Payouts rows appear once the ledger has payout entries. |
| W-15 | Milestones tab | No client milestone list is designed (the list is on WEB-CLIENT-009) | `/projects/{id}/milestones` uses the designed milestone rows of WEB-CONTRACTOR-005 with the client's amounts; `/projects/{id}` opens the milestone that needs attention until WEB-CLIENT-009 exists. |
| W-16 | WEB-CLIENT-013 pending | "Fund this milestone", "≈ £ estimate at today's rate" | Hidden until the funding screens (WEB-CLIENT-007/016); no endpoint gives today's rate, so a pending milestone shows NGN only. |
| W-17 | Evidence, receipts, ledger references (EV-2118, R-3307, T-2417) | Human-readable references | The API has UUIDs only: screens show the first 8 characters in mono. |
| W-18 | WEB-CONTRACTOR-003 dashboard | "Paid to you", the BoQ item on each card, the track record | "Paid to you" comes from the MX-06 mock behind `IBH_MOCKS` and is hidden without it; the BoQ item (contractor BoQ stage) and track record (MX-23) aren't shown. "Needs you" lists milestones the supervisor sent back. |
| W-19 | WEB-CONTRACTOR-005 milestones and claim | Evidence rows from ops checklist templates, supplier deductions, the supervisor card, "Client: name", BoQ / Evidence / Orders tabs | Like W-10, the open milestone lists the supervisor's captures; deductions need MX-05 and names MX-26, so "For you on release" equals the milestone amount; the other project tabs stay hidden until built (W-1). |
| W-20 | WEB-CONTRACTOR-006 sent back | A note per checklist item, "Start rework", "Dispute this rejection" | The backend keeps one note per verification (shown as the supervisor's words) and passed / not ready per item; "Start rework" has no backend step, so the screen offers "Claim {milestone} again"; disputing a rejection is not built (C-11, MX-25). |
| W-21 | WEB-OPS-006 queue | "Resolved 14" tab, "Unassigned", "[2 business days]" target, "Raised by Contractor" | No dispute list (MX-10) and no assignment in the backend: only open disputes are listed, the status is "Waiting for a proposal" or "Waiting for 2nd approver", and the placeholder target is left out. Only the client can raise a dispute (backend), so "Raised by" says Client. `/ops` opens on this queue until WEB-OPS-002 exists. |
| W-22 | WEB-OPS-006 resolution | Timeline with names, "Disagree", supplier split of the money held | The timeline is real, read from `GET /ops/audit` (the milestone's and the dispute's entries; no MX-10 mock needed), with people by role and "you". "Disagree" isn't built: the backend can't withdraw a proposal. Money held shows the milestone amount only (supplier orders need MX-05). The proposer's note comes from the audit entry. |
| W-23 | WEB-PUBLIC-010 sign-in | Footer links Privacy, Terms, Help; "3 attempts left"; the country picker | The footer links wait for their pages (W-2) and the attempts count isn't shown (B-1). The calling codes are a static list (`web/src/common/countries.ts`, common countries first); the backend checks and normalises the number. The NDPA consent card comes with W5b, after backend PR #67. |
| W-24 | WEB-OPS-001 ops sign-in | "Work queue" landing; "[company-domain]" in the email field | Staff sign in at `/ops/sign-in` with their work email, as designed; the placeholder domain isn't shown. The landing is the Stage 4 version of WEB-OPS-002 (W8), so `/ops` still opens on Disputes. The signed-out page is used by every portal. |
| W-25 | WEB-CLIENT-002 and WEB-OPS-001 session expired | "You were approving Blockwork to Lintel"; "Not now" | The app doesn't track the action in progress, so the sheet says the person stays on the page. The code goes to the account's email, else its phone by SMS, and is entered in the sheet, so nothing on the page is lost. "Not now" signs out (the session can't go on without signing in). |
| W-26 | WEB-CONTRACTOR-001 accept an invitation; WEB-SUPPLIER-001 supplier onboarding | `/invite/:token`, accept and decline; supplier profile, address and payout steps | Not built: the backend has no invitations (MX-02) or supplier accounts (MX-04). A contractor invited by phone is attached to the project already and lands on it at first sign-in. |
| W-27 | Consent card (WEB-PUBLIC-010 card 10) | Links to the Terms of use and Privacy policy; "withdraw consent later in Settings › Privacy" | **Launch blocker:** the documents aren't written yet. The card names them with their version (TERMS_VERSION / PRIVACY_VERSION, placeholder `2026-10-22`) and has no links; withdrawing says "by contacting us" until Settings exists. Only clients and contractors are asked (ops are staff; decided 2026-10-22). |
| W-28 | WEB-CLIENT-001 client onboarding | Email field (for a phone sign-up), "You'll pay in £ / $ / €", step 3 notification order, the empty dashboard | Not stored by the backend, so not asked: adding an email changes a sign-in identifier (needs a code); the currency is chosen per project and at funding (W6); notification preferences have no field. Two steps (details, location and time zone); the empty dashboard comes with the client home (W6). |
| W-29 | WEB-CONTRACTOR-002 contractor onboarding | Title, business name and email in step 1; "Changes are checked before the next payout"; "Start the BoQ"; "Invitation accepted" | Title, business name and email aren't stored; changes aren't checked by the backend, so that sentence is dropped; "Start the BoQ" waits for the BoQ editor (W7); there are no invitations (MX-02). The home's "Getting ready" shows profile, payout account and BoQ. |
| W-30 | Geofence map (WEB-CLIENT-004, later 011/012) | A styled street map | Leaflet 1.9.4 with OpenStreetMap tiles for local and staging (credited on the map). **Launch item:** OpenStreetMap's free tiles aren't for production traffic, so production needs a tile provider with a key (MapTiler or Stadia), a one-line change in `common/map/geofence-map.tsx`. Added for keyboard users (not in the design): "Can't use the map?" sets the pin by coordinates and a square boundary around it. |
| W-31 | WEB-CLIENT-003 create project; WEB-CLIENT-006 quote checker | Contractor's name and email, an area list; the quote check's quantity ranges, step-by-step progress, kept results, "Send back with these notes" | The backend invites a contractor by phone only and stores neither name nor area, so the area is typed into the address. The quote check flags prices only (no quantity ranges), answers in one step and keeps nothing, so the results show until the page is left; sending the BoQ back needs MX-08. |
| W-32 | WEB-CLIENT-003 set-up tracker; WEB-CLIENT-004 locked site; WEB-CLIENT-005 | "Engr. Obi accepted", the supervisor's name and body, "Invitation sent · Resend", "Ask our team to change it", "Send back for changes" | Names wait for MX-26 and invitation states for MX-02, so the tracker says "Contractor added" and "Assigned". There is no contact page for asking ops to change a locked site (W-2). Sending the BoQ back needs MX-08. |
| W-33 | WEB-CLIENT-007 / 016 funding | "Escrow release fee ([X]%)", "Card processing", a rate "held for [15 minutes]", and the currency fixed to GBP | The backend has one fee (`fee_bps`), shown as "Funding fee"; the placeholders and the hold time are left out (the checkout fixes the rate). The client picks GBP, USD or EUR on the page. The amounts come from `GET /funding/quote` (backend PR #74), which records nothing. |
| W-34 | WEB-CLIENT-008 home; WEB-CLIENT-009 overview | The notification bell, "Your contractor hasn't joined yet · Resend", the supervisor and contractor cards, visit history and spot checks, the live walkthrough | Not available yet (MX-11, MX-02, MX-26, MX-24, MX-14) or P2, so not shown. The home is at `/projects` (W-6). Amounts are in the client's currency where the ledger matches each payment, else naira. |
| W-35 | WEB-CLIENT-012 site map | A capture's card opening on the map, "Open evidence ›" | Each capture is listed beside the map with its time, who captured it and accuracy (the map is never the only way to read it); evidence detail needs MX-07, so there is no "Open evidence" yet. |
| W-36 | WEB-CLIENT-018 weekly reports | "Next one due Fri 18 Dec", the report's progress table and money lines | The due date isn't served; the report is shown as the agent wrote it (its own tables included), read from the list (MX-13). |
| W-37 | WEB-PUBLIC-001 to 009 public site | Square-bracket placeholders (prices, fees, the escrow partner and regulator, company name and RC, office address, WhatsApp and email, response time, supervisor rate, vetting time, DPO), the pilot testimonials, the hero and report samples ("North wall at lintel level", "£4,200.00", "4-bedroom bungalow, Lekki"), the contact form, "Invitation email", "Apply now", the legal text | Every company value lives in `web/src/features/public/site.ts`, all null: a section or line that needs one stays hidden, and Pricing says "Pricing is being finalised" (filling the file needs no other change; `e2e/public.spec.ts` fails if a `[…]` placeholder is ever shown). Testimonials are hidden until real quotes are collected with consent. Illustrations are neutral, with no names or amounts. No contact form (no endpoint): Contact lists the channels, or says they're on their way. Contractors are added by phone only (MX-02), so there's no invitation email or link. Supervisors apply in the Android app, which isn't out yet, so "Apply now" becomes "Tell us you're interested" (to Contact). Privacy and Terms render `web/content/legal/privacy.md` / `terms.md` and say "being finalised" until the lawyers supply them; the consent card links to both. A signed-in visitor at `/` goes to `/home`. Only production is indexed (`robots.txt`, `sitemap.xml` with `IBH_SITE_URL`). |
| W-38 | WEB-CONTRACTOR-004 BoQ editor | "Agreed contract sum" with its mismatch error, "Client sees, estimate ≈ $", "Version 2", "Compare with version 1", "Saved 16:42 · 2 of 3 comments addressed", the "Sent back" state, drag and drop between milestones | The backend has the client's budget, not a contract sum: the editor shows the lines total against the budget (over budget is a warning; the backend allows it) and never sends a total, so `boq_total_mismatch` can't happen. No rate before funding (B-6), no BoQ versions or comments, no send-back (MX-08), and the only save is the submit (PUT), so unsent changes are kept in the browser and leaving warns first. Lines move with a "Move to" menu (keyboard friendly). Submitting saves the BoQ and records the contractor's approval, as the design says. In review the contractor can revise it after a warning that every approval is cleared (the backend clears them). The price-index hint matches lines like the backend's quote check and flags lines more than 15% above; it never blocks. |
| W-39 | WEB-CONTRACTOR-008 payouts | Transfer reference ("P-0912"), "Advice (PDF)", "Retrying", "less ₦2,172,000 paid to Ugwu" | The page is built from the contractor's milestones (released, held, not funded) and the saved payout account, with "Change payout account" (the onboarding form, now shared in `features/payouts/account.tsx`). A row says "Released" with the release time; the transfer's own reference and status need payout history (MX-06; proposal below), the advice PDF needs MX-22, and supplier payments come with material orders. |
| W-40 | WEB-CONTRACTOR-009 profile | COREN and CAC check badges, "on iBackHome since", "3 of 4 claims verified the first time", "1.3 days", "disputes decided against you", "evidence rejected or flagged", "About the business", "Clients can see / never see" | Shown: the name (edit through `PATCH /me`), country, phone or email, "Payout account name matched by the bank", project counts, and three counts worked out from the contractor's milestones (verified, released, sent back now). The rest needs contractor vetting and history (MX-23); clients can't open a contractor's profile yet (MX-26), so the visibility card isn't shown. |
| W-41 | WEB-CONTRACTOR-007 material requests | Request materials from a verified supplier, order statuses | Moved to the materials stage with WEB-CLIENT-019 and the supplier portal: a contractor can't choose a supplier or see orders without a supplier list and a project order list (MX-04, MX-05; Abigail's folder). Orders stays off in the contractor top bar. |
| W-42 | WEB-OPS-002 overview | Failed releases and Reconciliation tiles, the Alerts panel with "Retry release" and "Compare records", the live map of all sites, "Today on site", the search box | Shown: the three queues with the oldest wait, projects by status, and the projects that need ops (BoQ waiting for ops, no supervisor on a live project, a dispute, a claim sent back). Money alerts and retry need MX-21; the project list doesn't carry sites, so there's no map of all sites; visits need MX-24; there's no search endpoint. |
| W-43 | WEB-OPS-004 projects | Client, contractor and supervisor names and countries; "Pause project"; "Supervisor and rotation" with the candidates, their load and declared relations; "Edit boundary needs a written reason and a second ops approval" | Names need MX-26, so the list says whether a contractor and supervisor are set. Pause needs MX-09 (no route). Choosing a supervisor needs the vetted-supervisor list (MX-15, W8b). The site is changed with the same editor as the client's, from "Change site"; the backend lets ops change it at any time with no second approval, and audits every change. Ops approve the BoQ from the project page (the final approval makes the project live). |
| W-44 | WEB-OPS-005 flagged evidence | The matched earlier capture side by side, "Distance 6 of 64", both hashes, signature, GPS distance to the edge, checklist item, supervisor note, both points on the site map | There's no single-evidence read (MX-07) and the flag doesn't say which capture it matched, so the screen shows the flagged capture, the server's reason, the three checks, when and where it was taken, accuracy, device and file hash. Accept, or reject with notes (required); a decision someone else made first is the designed conflict. |
| W-45 | WEB-OPS-010 weekly reports | The reviewer's name, "2 days late", "Ops edit" of the text, "Regenerate draft", "Runs this week" | `POST /reports/{id}/review` approves the draft as it is (no edit, no reject, no regenerate) and the backend lets ops review any draft. Reports are read project by project (MX-13). The runs summary needs MX-18. |
| W-46 | WEB-OPS-009 price index | Source supplier per item, "Change waiting" with accept or reject, "Remind 2 suppliers", "Add item" | Read-only: item, unit, index price, low to high, number of suppliers, last seen, stale. Changes need MX-16. |
| W-47 | WEB-OPS-011 audit log | Actor names, free-text search, "Export CSV", the Agent runs tab | Filters by exact action (actions already seen are suggested), object type, object id and period; 50 at a time with "Show 50 more"; an entry opens before and after. Actor names need MX-26 (the id is shown, "system" when none), export MX-22, agent runs MX-18. |
| W-48 | WEB-OPS-003 vetting | The application detail and the decision | Only the queue (registration body and number, submitted, waiting). Ops can't read the applicant's name, phone or guarantors (MX-15), and approving means confirming the guarantors, so no decision is offered until W8b. |
| W-52 | Brand refresh (23 Oct 2026), all screens | The house-and-eye mark in a navy square with "iBackHome" in Inter; primary #131F39; copy and sample data set in Enugu ("For Nigerians abroad building in Enugu", "Enugu price index", "Area, Enugu", Enugu neighbourhoods, times "in Enugu (WAT)") | **Logo:** the supplied artwork (house with an eye above the waves, "iBackHome" beneath), as trimmed PNGs: blue on light, white on navy, and the house-and-eye mark alone for the favicon and tight bars (`05-assets/logo/`, `web/public/brand/`, `web/src/app/icon.png`); every screen, prototype and the design-system page use them. Vector files will replace the PNGs. **Colour:** Navy 900 (primary) is #00022E, with hover #10144A and raised-on-navy #1E2260 derived from it, in every token file and screen. **Nationwide:** iBackHome serves projects anywhere in Nigeria, so the copy says so; times read "Nigerian time (WAT)"; the price index is "the price index"; a new project's address is street, town or city, and state (all 36 states and the FCT); the map starts on the whole country; sample projects, suppliers and people moved to Lagos and Abuja. The PNG screenshots still show the old logo, colour and copy: the HTML is current. **For the owners:** the backend's price index holds Enugu survey prices (pricing by state is a backend item), and the root CLAUDE.md, the PRD, the Spec and backend copy (report agent, seed data, API examples) still say Enugu. |

## Colours outside the Stage 2 token set

All hex values in `screen.html` style attributes and board CSS are mapped to `var(--ibh-*)`. Values on approved boards that are not in the Stage 2 token set are kept as `supplementary` tokens (`x-*` in tokens.json / tokens.css) so the screens render as approved; confirm or replace them:

| Token | Hex | Used for |
|---|---|---|
| `--ibh-x-placeholder-border` | `#C2CAD5` | Dashed border of "coming soon" and empty placeholders |
| `--ibh-x-map-land` | `#E6E9ED` | Map illustration: plots |
| `--ibh-x-map-block` | `#E2E6EB` | Map illustration: buildings |
| `--ibh-x-whatsapp-wallpaper` | `#ECE7DF` | WhatsApp chat background in phone mocks (third-party UI) |
| `--ibh-x-whatsapp-bubble-out` | `#DCE8FB` | Outgoing chat bubble in the assistant mock |
| `--ibh-x-chat-bg` | `#ECE9E4` | Chat background in the invitation mock |
| `--ibh-x-on-navy-muted` | `#9AA6BB` | Small caps headings in the footer; disabled text on navy |
| `--ibh-x-ok-on-dark` | `#8FD3AE` | Success icon on a navy toast |
| `--ibh-x-bad-on-dark` | `#F1C4BF` | Error text on a navy surface |
| `--ibh-x-bad-icon-on-dark` | `#F4A79F` | Error icon on a navy toast |
| `--ibh-x-destructive-hover` | `#912018` | Destructive button hover |

Raw hex left in `style` attributes after mapping: none.
SVG `fill` / `stroke` presentation attributes keep raw hex (CSS variables do not work there); every one of them is a token value: #00022E ×225 (Navy 900; #131F39 until 23 Oct 2026), #FFFFFF ×136, #3A4354 ×75, #2F5FC4 ×52, #8A5300 ×35, #B42318 ×28, #E6E9ED ×25, #1E6B45 ×16, #0B1324 ×9, #5F6878 ×8, #E2E6EB ×5, #FDF1D8 ×5.

## 6. P2 items shown only as placeholders

| FR | Item | Where | What is shown |
|---|---|---|---|
| FR-21 | Live video walkthrough | WEB-CLIENT-021 (desktop + mobile), "Coming soon" card on WEB-CLIENT-009, add-ons on WEB-PUBLIC-003 | Dashed "Coming soon" card that links to evidence and reports. No booking form, times, price or video SDK. |
| FR-22 | Land and title verification | WEB-CLIENT-022 (desktop), add-ons on WEB-PUBLIC-003 | Dashed "Coming soon" card linking to pricing. No request form, ops workflow or price. |

PRD cut order if behind schedule: 1. WhatsApp assistant (P1, designed: WA-CLIENT-002), 2. live walkthroughs (P2 placeholder), 3. land verification (P2 placeholder).

## Items not designed

Listed so nobody invents them silently. Each needs a design decision before it is built.

- **AU-03 code message** (the WhatsApp/SMS/email OTP message itself). Sign-in states are designed; the message copy is not.
- **NS-06 ops alert email template.** Alert settings (WEB-OPS-013) and console alerts (WEB-OPS-002) exist; the email layout does not.
- **Client emails other than "milestone verified" and "weekly report"** (released, dispute opened/resolved, invitation): reuse EMAIL-CLIENT-001's layout.
- **Weekly report PDF layout** (CM-09): only the web viewer and the download link are designed.
- **Release receipt PDF and payout advice PDF**: links only.
- **Visit history page** for the client (CD-04): the overview card links "Visit history ›", the page itself is not designed.
- **Mobile-web frames for some portal screens**: contractor portal screens (WEB-CONTRACTOR-003…009) and several client set-up and ops screens have desktop frames only. Ops is desktop-only by design; for the others follow the portal's mobile pattern.
- **Payout "reversed" state** and **material order "cancelled" detail**: chips only.
- **Paused and completed project views** (Stage 1 G-30): described, not drawn beyond the ops "Paused" chip and offline/paused banners.
- **Public-site photography, Android launcher icon, favicon set, social share images.**
- **Map tile style**: maps are drawn as illustrations; the tile provider and style are not chosen.

## Placeholders (values in square brackets)

Every screen's spec lists its own placeholders in section 8; fixtures carry a PLACEHOLDER notice. Across all screens:

`[REGISTERED COMPANY NAME]` (9), `[NUMBER]` (9), `[OFFICE ADDRESS]` (9), `[X]` (4), `[£ FEE]` (4), `[2 business days]` (4), `[£ TOTAL]` (3), `[DPO EMAIL]` (2), `[DATE]` (2), `[3 working days]` (2), `[24 hours]` (2), `[10%]` (2), `[Site photo — pilot project]` (1), `[Name]` (1), `[City]` (1), `[£ PRICE]` (1), `[$ PRICE]` (1), `[€ PRICE]` (1), `[TO BE CONFIRMED]` (1), `[HOW THIS IS CHARGED — TBC]` (1), `[PRICE]` (1), `[PAYOUT METHOD AND TIMING — TO BE CONFIRMED]` (1), `[₦ RATE]` (1), `[placeholder until pilot rates are set]` (1), `[TYPICAL TIME — TO BE CONFIRMED]` (1), `[LICENSED ESCROW PARTNER]` (1), `[REGULATOR]` (1), `[DPO NAME]` (1), `[TRUST EMAIL]` (1), `[RESPONSE TIME]` (1), `[WHATSAPP NUMBER]` (1), `[CONTACT EMAIL]` (1), `[OPENING HOURS]` (1), `[RETENTION PERIODS]` (1), `[HOSTING LOCATION]` (1), `[AMOUNTS TBC]` (1), `[NIGERIAN LAW AND COURTS — TO BE CONFIRMED]` (1), `[LEGAL EMAIL]` (1), `[Video · EV-2119 · full size]` (1), `[Photo · EV-2102 · full size]` (1), `[Photo · EV-2121 · full size]` (1), `[Photo · tap to enlarge]` (1), `[1 hour]` (1), `[partner ref]` (1), `[15 minutes]` (1), `[3 days]` (1), `[30 days]` (1), `[48 hours]` (1), `[model version]` (1), `[2246, 2248]` (1), `[2 business hours]` (1), `[7 years]` (1), `[8 hours]` (1), `[30 minutes]` (1), `[12 hours]` (1), `[10 s]` (1)

Plus all sample people, phone numbers, amounts, FX rates, dates and IDs (Chioma Nwosu, Engr. Obi, Ifeanyi Okafor, Chidi Nnaji, Nnamdi Ugwu, Adaeze U., Ngozi E., £1 = ₦1,950.00, R-3307 …). They are fictional and must not ship.

## Personal data and secrets

All people, businesses, phone numbers and account numbers are fictional. UK numbers use the Ofcom drama range (+44 7700 900xxx); Nigerian numbers and bank accounts are masked or use +234 800 000 0xxx in fixtures; fixture emails use example.com; the product domain ibackhome.ng in email mocks is a placeholder. No API keys, tokens or secrets are included (JWTs and keys in fixtures are the literal string PLACEHOLDER).

## Additions to the requested folder structure

- `05-assets/fonts/` holds the Inter and JetBrains Mono WOFF2 files (with their SIL OFL licences) so every `screen.html` opens offline with the right fonts; `fonts.md` sits where requested.
- `05-assets/logo/README.md` and `05-assets/images/README.md` explain the assets (since 23 Oct 2026 the logo is a PNG, the designs' only raster images).
- `03-prototype-flows/index.md` lists the flows and maps each step to a screen ID.
- Each screen folder may contain more than one PNG per variant (`desktop-02-<state>.png` …) and, for the sign-in states, empty states and the invitation panel, `card`, `tile` and `panel` screenshots; the names are explained in README.md.

## Package size

| Folder | Files | Size |
|---|---|---|
| 00-overview | 4 | 0.1 MB |
| 01-design-system | 7 | 0.6 MB |
| 02-screens | 590 | 14.9 MB |
| 03-prototype-flows | 6 | 0.3 MB |
| 04-api-mapping | 4 | 0.1 MB |
| 05-assets | 21 | 0.3 MB |
| 06-build-plan | 2 | 0.1 MB |
| CLAUDE.md | 1 | 0.0 MB |
| PACKAGE-REPORT.md | 1 | 0.0 MB |
| README.md | 1 | 0.0 MB |
| index.html | 1 | 0.1 MB |
| manifest.json | 1 | 0.2 MB |
