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

- Captures must upload within [48 hours] of being taken, or they're rejected.
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
| C-1 | AND-SUPERVISOR-007 (offline frame), AND-SUPERVISOR-014 (push), Stage 13 assumption list | Captures not uploaded within [48 hours] are rejected | Spec: 72 h upload window, app warns at 48 h | Decide. Until then make it a server config value defaulting to 72 h and fill the copy from config. |
| C-2 | WEB-OPS-005, Stage 13 assumption list | Near-duplicate flagged at distance 10 or less of 64 | Spec: Hamming distance ≤ 8 | Decide. Config value defaulting to 8; show the configured value. |
| C-3 | AND-SUPERVISOR-011 | Supervisor can "Edit the draft" before marking reviewed | Stage 1 G-17: no free-text editing of AI output; Spec has review only | Decide. If kept, needs MX-13 and the edit must keep the AI label and citations. |
| C-4 | WEB-CLIENT-020 | In-app notifications screen | Stage 1 G-25: no in-app inbox; Spec has no feed endpoint | Approved in Stage 7; needs MX-11. |
| C-5 | WEB-SUPPLIER-004 | Order "Payment on hold" state | material_orders.status has no "on hold" | Backend decision (MX-05). |
| C-6 | WEB-OPS-012 | User status "Deactivated" | users.status: active, suspended | Backend decision or drop the option. |
| C-7 | WEB-OPS-004 | Editing a locked boundary needs a reason and a second ops approval | Spec: ops can change the site any time; audited | Treat as UI policy until the backend supports it. |
| C-8 | X-Empty board (WEB-CLIENT-025, WEB-CONTRACTOR-011, WEB-SUPPLIER-009, WEB-OPS-014) | 6 empty-state buttons render with browser-default styling because their style rule is scoped to another board class | Design system: secondary button | Build them as secondary buttons. The screenshots show the board exactly as approved. |
| C-9 | Stage 5 funding success frame | "Funded" chip in info tone | Every other board: neutral | Use neutral (state-to-ui.md). |
| C-10 | WEB-CONTRACTOR-006 | Dispute "Under review" chip in bad tone | Evidence "Under review" is warn | Keep Disputed (bad) for disputes, warn for evidence. |
| C-11 | Stage 1 G-12 vs Spec | Contractor can dispute a supervisor rejection | Spec state machine only has verified → disputed | Approved assumption; needs a backend rule (dispute without a milestone state change). |

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
SVG `fill` / `stroke` presentation attributes keep raw hex (CSS variables do not work there); every one of them is a token value: #131F39 ×225, #FFFFFF ×136, #3A4354 ×75, #2F5FC4 ×52, #8A5300 ×35, #B42318 ×28, #E6E9ED ×25, #1E6B45 ×16, #0B1324 ×9, #5F6878 ×8, #E2E6EB ×5, #FDF1D8 ×5.

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
- `05-assets/logo/README.md` and `05-assets/images/README.md` explain the assets (the designs use no raster images).
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
