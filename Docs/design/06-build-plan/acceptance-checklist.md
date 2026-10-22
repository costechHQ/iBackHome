# Acceptance checklist

One block per screen. Tick each item when the screen is built, then re-run lint, type-check and tests. "States" lists every designed frame; "Rules" comes from the screen's spec section 6. Do not tick a screen whose data still comes from a mock adapter without noting the MX id.

## Web build stages (W0–W4, the web gate)

The repo builds the web app in stages W0–W4 (ADR 0004); the screen blocks below are ticked as each stage builds them.

### W0 · Repo, contract and Spec (no screens)

- [x] Handoff committed at `Docs/design/`, kept out of every build (the web image's build context is `web/`)
- [x] CODEOWNERS: `/web/` and `/mobile/` → Gabriel
- [x] Next.js (App Router) + TypeScript strict + Tailwind CSS v4 scaffold; the Spec's `common/` and `features/` folders plus `app/` for routes only (ESLint enforces the import rules)
- [x] Generated API client (`web/src/common/api/`, from the backend's OpenAPI) and a CI drift check (`api-contract`)
- [x] CI `web-ci`: eslint, prettier, tsc, next build, Vitest, Playwright against next start, Docker image
- [x] Docker image (standalone, Node), `web` in local Compose and staging Compose, Caddy route on its own hostname
- [x] ADR 0004 and the Spec update (separate commit)

### W1a · Tokens, auth proxy, API wrapper, helpers (no designed screens)

- [x] Tokens copied from `01-design-system/tokens.css` (drift test) and mapped into Tailwind with `@theme inline`; Tailwind's default colours, radii and shadows removed; no hex in the theme
- [x] Inter and JetBrains Mono self-hosted with `next/font/local` (latin + latin-ext for ₦)
- [x] Auth BFF: OTP exchange, httpOnly cookies, same-origin `/api/v1/*` proxy, single-flight refresh with a 30 s reuse window, Origin check on writes, token routes blocked
- [x] Role guards: `src/proxy.ts` (session present, token fresh) + each portal layout (role from `GET /me`)
- [x] API wrapper: generated client, `ApiError` → `error-codes-to-ui.md` patterns (409 = conflict), one Idempotency-Key per write action
- [x] Money helper (BigInt minor units, decimal-string FX, no floats); time helper (client zone / WAT, UTC on hover)
- [x] Status chip registry generated from `state-to-ui.md` (drift test, backend enums checked)
- [x] Allowed-actions helper for milestones and disputes (two different ops users for either outcome)
- [x] Plain OTP sign-in at `/sign-in` with the WEB-PUBLIC-010 copy for the backend's real errors (designed AuthCard states come in the auth stage)
- [x] Signed-in pages, sign-in and the proxy send `Cache-Control: no-store` (Playwright test)
- [x] Gaps logged: MX-19 (sign-out only clears cookies); backend differences B-1 to B-5 in PACKAGE-REPORT

### W1b · UI kit, shells, system pages

- [x] UI kit in `web/src/common/ui/`: buttons (loading keeps its colour), text field, select, error summary, segmented control, status chip, alert, toast, skeleton (slow after 10 s), empty state, card, avatar, table, dialog and alert dialog, money display, escrow trust line, wordmark, time with UTC on hover
- [x] Tokens only: a test fails on any hex/rgb colour or Tailwind arbitrary value in `src/`
- [x] Shells: ClientTop (project switcher, account menu), project header + ClientTabs, ClientNav (mobile), ConTop, ops sidebar with queue counts and environment badge
- [x] System states (WEB-CLIENT-024): 404, 500 with reference, 403, 409 conflict, form validation, session expired (can't be dismissed, returns to the page), offline bar (follows the connection), loading skeleton, toasts, confirmation and destructive dialogs
- [x] Dialogs trap focus and return it to the opener; Escape doesn't close a dialog about money; the safe choice is on the left
- [x] axe: no WCAG 2.1 AA violations in any frame at 960, 1280 and 390 px (`e2e/states.spec.ts`)
- [x] Not built yet, logged as W-1 to W-8 in PACKAGE-REPORT (hidden links, Help, bell, ops search and session timer, a dropped placeholder, the `/` route conflict)

### W2 · Client milestone release

- [x] WEB-CLIENT-013 milestone detail in all six states, against the real API (local stack, seed driver): stepper, state panel, evidence checklist, supervisor's verification, money (client currency, NGN, rate at funding), activity in the client's time zone
- [x] Approve and dispute only on Verified and only for the project's client; no approve button while disputed (stack test)
- [x] WEB-CLIENT-014 approve in 3 taps on a phone (detail → review → confirm), desktop confirm dialog that ignores Escape; 409 shows the designed conflict state
- [x] Receipt as a print-styled page (MX-22)
- [x] WEB-CLIENT-015 raise a dispute and "Release paused"
- [x] WEB-CLIENT-010 evidence gallery (read-only) with the three checks on every item; rejected captures never shown to the client
- [x] WEB-CLIENT-017 ledger with escrow now (MX-20, computed), summary, filters and a CSV made in the browser
- [x] axe: no WCAG 2.1 AA violations on these screens at 1280 and 390 px with real data
- [x] Mocks behind `IBH_MOCKS`: MX-03 (pays to), MX-10 (dispute reason). Gaps logged: MX-26, MX-27 (new), W-9 to W-17

### W3 · Contractor claim and ops disputes

- [x] WEB-CONTRACTOR-003 dashboard at `/c`: greeting in WAT, "Needs you" (milestones sent back), one card per project with released and held NGN
- [x] WEB-CONTRACTOR-005 milestones with the project row (‹ Projects, title, status, Milestones tab); "Claim milestone" only on Funded, confirm dialog, 409 as the designed conflict; NGN only
- [x] WEB-CONTRACTOR-006 sent back: the supervisor's notes, each item Accepted / Not ready, money still held, "Claim again" (the stack test claims it)
- [x] WEB-OPS-006 queue from `GET /ops/queue` with project, milestone and money held; Disputes in the ops sidebar
- [x] WEB-OPS-006 resolution: real timeline from the audit log, evidence by supervisor / contractor, money held; step 1 proposes with a required note, step 2 a different ops user confirms the same outcome; the same user confirming gets 409 `second_approval_required` (stack test, two seeded ops users)
- [x] axe: no WCAG 2.1 AA violations on these screens (contractor at 1280 and 390 px, ops at 1440 px) with real data
- [x] Mocks behind `IBH_MOCKS`: MX-06 (paid to you). Backend: a second ops user in `seed.py` (#62), proposal fields on the ops queue (#63). Gaps logged: W-18 to W-22

### W4 · The web gate

- [x] Gate journey through the screens on a fresh project each run (`e2e/stack/gate.spec.ts`): fund → supervisor captures → the contractor claims → supervisor verifies → the client approves in three taps → simulated escrow releases → receipt and ledger row; then the dispute path: the client disputes, ops 1 proposes rework, ops 2 confirms, the milestone is back to Funded and the contractor can claim again
- [x] Seed driver `--new-project`: the client creates the project and site, the contractor submits a BoQ, client, contractor and ops approve, ops assigns a supervisor (all through the real API)
- [x] Dual approval can't be bypassed from any screen (`e2e/stack/gate-guards.spec.ts`): Approve only for the project's client and only on Verified; none on a dispute; none for the contractor; the proposer of a dispute resolution has no approve control; the API (through the web proxy) refuses the contractor and ops with 403
- [x] Each portal refuses the other roles (403 page); signed-out visitors go to sign-in from every portal route; every portal route is `no-store`
- [x] The client can approve with the keyboard alone
- [x] Production-like server (no `IBH_MOCKS`): no mocked data is shown
- [x] CI: `.github/workflows/web-stack.yml` runs every stack test against Docker Compose from an empty database (seed, simulator, driver), on web and backend changes; simulated locally from an empty database: 22 of 22 pass
- [ ] On staging: waits for a web host (the backend is moving to Render, ADR 0003; the web app has none yet)

### W5a · Sign-in and session

- [x] WEB-PUBLIC-010 sign-in at `/sign-in`: split screen on desktop, card on mobile; Phone / Email switch, country picker (search, common countries first, keyboard), WhatsApp or SMS, then six code boxes (paste fills them) with the expiry countdown and resend after 30 s; Back and Change keep what was typed
- [x] Every designed sign-in state from the backend's real answers: wrong code, too many attempts (code cancelled), expired, rate limited with the wait from `Retry-After`, channel unavailable (503, the channel marked and the other chosen), send failed (502, "Try again")
- [x] WEB-OPS-001: staff sign-in at `/ops/sign-in` (work email), signed-out visitors to `/ops/*` go there; the signed-out page after every sign-out
- [x] WEB-CLIENT-002 and the desktop frame: when a session ends, the code is sent to the person and entered in the sheet or dialog, so they stay on the page; it can't be dismissed and "Not now" signs out
- [x] Fixed: the API client lost the backend's error code (openapi-fetch had already read the body), so only status-based states showed; regression test added
- [x] axe: no WCAG 2.1 AA violations on sign-in, ops sign-in and signed-out at 1280 and 390 px, and on the code step
- [x] Backend PRs for W5b: #67 (`PATCH /me`, NDPA consent; reviewer Christopher), #68 (contractor payout account; reviewers Christopher and James). Gaps logged: W-23 to W-26

### W5b · Onboarding and consent

- [x] Portal layouts send a client or contractor to `/welcome` while consent or a required step is missing (one tested rule, `features/auth/onboarding/steps.ts`); ops never onboard
- [x] NDPA consent card first: both boxes required, records agreement to the current versions (`POST /me/consent`), an outdated version is refused and shown again; "Don't agree — sign out"
- [x] WEB-CLIENT-001: details (full name; the sign-in phone or email shown as verified) and location (country, common first; time zone from the browser, all zones), saved with `PATCH /me`
- [x] WEB-CONTRACTOR-002: details, then the payout account: bank list, "Account found NAME", save, saved card with the number masked, "Change account" (`/banks`, `/me/payout/recipient`)
- [x] Contractor home: "Getting ready" (profile, payout account, BoQ) on draft projects
- [x] axe: no WCAG 2.1 AA violations on every onboarding step at 1280 and 390 px
- [x] Backend: seed.py records consent for the seeded people (#71, reviewer James). Gaps logged: W-27 to W-29
- [ ] Legal: the real terms of use and privacy policy, their versions and links (launch blocker, W-27)

### W6a · Project set-up

- [x] WEB-CLIENT-003: projects list with set-up progress and the next step, the empty state, create a project (validation with the design's Nigerian-number message) that invites the contractor by phone, and the six-step set-up tracker
- [x] WEB-CLIENT-004: site pin and boundary on a street map (drag the pin, click corners, undo, clear), the 25 m tolerance band, pin-outside error, saved, locked once active; a keyboard way to set the site
- [x] WEB-CLIENT-005: BoQ by milestone with every line, total against budget, the three approvals, the final approval (needs a saved site) that makes the project active
- [x] WEB-CLIENT-006: quote check of the submitted BoQ or a PDF, flagged lines first, the over-index total, and the price index
- [x] Set-up tabs (Set-up, BoQ, Quote check, Site) while a project is draft or in BoQ review; `/projects/:id` opens the tracker for those
- [x] Unit tests for the set-up steps, the map geometry and the quote figures (BigInt, no floats); stack test of the whole set-up through to an active project; axe clean at 1280 and 390 px
- [x] Gaps logged: B-6 (projects in naira), W-30 to W-32, MX-08 proposal
- [ ] Production map tiles (W-30, launch item)

## Stage 3 · Public site

### WEB-PUBLIC-001 · Landing page

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/`
- [ ] State: Desktop
- [ ] State: PUB-01 · Landing
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- [ ] Rule: Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-002 · How it works

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/how-it-works`
- [ ] State: Desktop
- [ ] State: PUB-02 · How it works
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-003 · Pricing

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/pricing`
- [ ] State: Desktop
- [ ] State: PUB-03 · Pricing
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: P2 placeholder only: no form, booking, times or prices. Do not build the feature.
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-004 · For contractors

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/contractors`
- [ ] State: Desktop
- [ ] State: PUB-04a · For contractors
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-005 · Become a supervisor

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/supervisors`
- [ ] State: Desktop
- [ ] State: PUB-04b · Become a supervisor
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-006 · Trust and safety

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/trust`
- [ ] State: Desktop
- [ ] State: PUB-05a · Trust and safety
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Rule: iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-007 · Contact

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/contact`
- [ ] State: Desktop
- [ ] State: PUB-05b · Contact
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-008 · Privacy policy

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/privacy`
- [ ] State: Desktop
- [ ] State: PUB-05c · Privacy policy
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-PUBLIC-009 · Terms

- [ ] Built at `web/src/features/public/ (new folder; the Spec lists no public-site feature)` (or the repo's equivalent); route `/terms`
- [ ] State: Desktop
- [ ] State: PUB-05d · Terms
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 4 · Auth and onboarding

### WEB-PUBLIC-010 · Sign in or sign up

- [ ] Built at `web/src/features/auth/` (or the repo's equivalent); route `/sign-in`
- [ ] State: Enter phone
- [ ] State: Enter phone
- [ ] State: Code
- [ ] State: Country selector Search, common countries first
- [ ] State: Email Code by email only
- [ ] State: Code entry 5-minute countdown, resend after 30 s
- [ ] State: Wrong code Attempts left shown
- [ ] State: Too many attempts Code cancelled
- [ ] State: Code expired After 5 minutes
- [ ] State: Rate limited Per number and device
- [ ] State: Channel unavailable Server: 503
- [ ] State: Send failed Server: 502
- [ ] State: Consent — first sign-up NDPA 2023
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Uses the generated API client for: `POST /auth/otp/request`, `POST /auth/otp/verify`, `GET /me`
- [ ] Responsive: matches the card, desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-PUBLIC-001 · Sign in (Android)

- [ ] Built at `mobile/lib/features/auth/` (or the repo's equivalent); route `SignInScreen`
- [ ] State: Enter phone
- [ ] State: Code
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Uses the generated API client for: `POST /auth/otp/request`, `POST /auth/otp/verify`, `GET /me`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WA-CONTRACTOR-001 · Invitation message (WhatsApp)

- [ ] Built at `backend/app/base/notifications/ (template)` (or the repo's equivalent); route `template: project_invitation`
- [ ] State: 1 · Invitation message (WhatsApp template)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- [ ] Mock adapter for MX-02, logged as a gap
- [ ] Responsive: matches the whatsapp frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-001 · Accept an invitation

- [ ] Built at `web/src/features/auth/` (or the repo's equivalent); route `/invite/:token`
- [ ] State: 2 · Invitation with project preview
- [ ] State: 3 · Confirm it's you
- [ ] State: 4 · Joined
- [ ] State: 5 · Declined
- [ ] State: 6 · Expired or already used
- [ ] State: 7 · Signed in with another number
- [ ] State: Invitation (contractor at a computer)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Uses the generated API client for: `POST /auth/otp/request`, `POST /auth/otp/verify`
- [ ] Mock adapter for MX-02, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-001 · Client onboarding

- [ ] Built at `web/src/features/auth/` (or the repo's equivalent); route `/welcome`
- [ ] State: Step 1 of 3 — Your details
- [ ] State: Step 2 of 3 — Location and currency
- [ ] State: Step 3 of 3 — Notifications
- [ ] State: Empty dashboard
- [ ] State: Step 2
- [ ] State: Empty dashboard
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-002 · Contractor onboarding

- [ ] Built at `web/src/features/auth/` (or the repo's equivalent); route `/welcome`
- [ ] State: Step 1 — your details
- [ ] State: Step 2 — payout account, name checked
- [ ] State: Step 2 — saved, number masked
- [ ] State: Home — waiting for your BoQ
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, MX-03, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-001 · Contractor onboarding (Android)

- [ ] Built at `mobile/lib/features/auth/` (or the repo's equivalent); route `ContractorOnboardingScreen`
- [ ] State: Payout — name found
- [ ] State: Payout — not found
- [ ] State: Home — waiting for BoQ
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, MX-03, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-001 · Supplier onboarding

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/welcome`
- [ ] State: Step 1 — business profile
- [ ] State: Step 2 — address and map
- [ ] State: Step 3 — payout recipient
- [ ] State: Awaiting ops verification
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-02, MX-03, MX-04, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-001 · Supervisor application and vetting status

- [ ] Built at `mobile/lib/features/auth/ (vetting; Spec puts vetting under backend supervision/)` (or the repo's equivalent); route `SupervisorApplicationScreen`
- [ ] State: 1 · Start application
- [ ] State: 2 · Registration
- [ ] State: 3 · NIN
- [ ] State: 4 · Guarantors
- [ ] State: 5 · Relatives who are contractors
- [ ] State: 6 · Review and submit
- [ ] State: 7 · Pending
- [ ] State: 8 · Rejected, with reason
- [ ] State: 9 · Approved
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `PUT /supervisors/me/profile`, `GET /supervisors/me/profile`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-002 · Permissions and capture key

- [ ] Built at `mobile/lib/core/ (signing keys) + mobile/lib/features/auth/` (or the repo's equivalent); route `PermissionsScreen, DeviceKeyScreen`
- [ ] State: 10 · Permissions
- [ ] State: 11 · Secure capture key
- [ ] State: 12 · Key ready
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- [ ] Uses the generated API client for: `POST /devices`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-001 · Ops sign-in and session

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/sign-in`
- [ ] State: Ops · sign-in (desktop only)
- [ ] State: Ops · landing — work queue
- [ ] State: Session expired · desktop (return to the same page)
- [ ] State: Signed out · desktop
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Uses the generated API client for: `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/refresh`, `GET /me`, `GET /ops/queue`
- [ ] Mock adapter for MX-19, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-002 · Session expired (mobile web)

- [ ] Built at `web/src/common/ (auth)` (or the repo's equivalent); route `(overlay on any client route)`
- [ ] State: Session expired · mobile web (bottom sheet)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Login is OTP only: 6 digits, valid 5 minutes, max 5 attempts, sent only on the channel chosen (no fallback). No passwords.
- [ ] Uses the generated API client for: `POST /auth/refresh`, `POST /auth/otp/request`, `POST /auth/otp/verify`
- [ ] Responsive: matches the mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-003 · Session expired and sign out (Android)

- [ ] Built at `mobile/lib/features/auth/` (or the repo's equivalent); route `SessionExpiredSheet, SignOutDialog`
- [ ] State: Session expired · Android (queue is safe)
- [ ] State: Sign out · Android (with unsent captures)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Uses the generated API client for: `POST /auth/refresh`, `POST /auth/otp/request`, `POST /auth/otp/verify`
- [ ] Mock adapter for MX-19, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 5 · Client project setup

### WEB-CLIENT-003 · Projects and create project

- [ ] Built at `web/src/features/projects/` (or the repo's equivalent); route `/projects, /projects/new, /projects/:id/setup`
- [ ] State: CS-01 · Projects — empty
- [ ] State: CS-01 · Projects — populated
- [ ] State: CS-02, CS-03 · Create project — with one inline error
- [ ] State: CS-05 · Set-up tracker, with supervisor assigned
- [ ] State: Projects
- [ ] State: Create project
- [ ] State: What Chioma sees meanwhile (set-up tracker row)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Uses the generated API client for: `GET /projects`, `POST /projects`, `GET /projects/{id}`, `GET /projects/{id}/boq`
- [ ] Mock adapter for MX-02, logged as a gap
- [ ] Responsive: matches the desktop, mobile, panel frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-004 · Site pin and geofence

- [ ] Built at `web/src/features/projects/ (geofence drawing) + web/src/common/ (map component)` (or the repo's equivalent); route `/projects/:id/site`
- [ ] State: Drawing the boundary
- [ ] State: Error — pin outside the boundary
- [ ] State: Saved
- [ ] State: Locked — project active
- [ ] State: Drawing
- [ ] State: Locked
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- [ ] Rule: The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- [ ] Uses the generated API client for: `PUT /projects/{id}/site`, `GET /projects/{id}`
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-005 · BoQ review and approval

- [ ] Built at `web/src/features/projects/` (or the repo's equivalent); route `/projects/:id/boq`
- [ ] State: CS-06 · BoQ review — over budget, waiting for the client
- [ ] State: CS-08 · Send back for changes
- [ ] State: All three approved — project active
- [ ] State: BoQ summary
- [ ] State: Confirm approval
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Uses the generated API client for: `GET /projects/{id}/boq`, `POST /projects/{id}/boq/approve`
- [ ] Mock adapter for MX-08, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-006 · Quote checker

- [ ] Built at `web/src/features/projects/ (calls quotes/check) ` (or the repo's equivalent); route `/projects/:id/boq/check`
- [ ] State: 1 · Choose what to check
- [ ] State: 2 · Checking
- [ ] State: 3 · Results — flagged lines first
- [ ] State: 4 · Price index reference
- [ ] State: Results
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Uses the generated API client for: `POST /quotes/check`, `GET /price-index`, `GET /projects/{id}/boq`
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-007 · Fund the first milestone

- [ ] Built at `web/src/features/dashboard/ (no escrow feature folder on web in the Spec)` (or the repo's equivalent); route `/projects/:id/fund/:milestoneId`
- [ ] State: CS-09 · Before you pay
- [ ] State: Hand-off to Stripe Checkout
- [ ] State: CS-10 · Payment received — waiting for escrow
- [ ] State: Funded — success
- [ ] State: Payment failed or cancelled
- [ ] State: Before you pay
- [ ] State: Waiting for escrow
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: iBackHome never holds client funds; copy must never say "your money is with iBackHome".
- [ ] Rule: Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.
- [ ] Uses the generated API client for: `POST /projects/{id}/funding`, `GET /projects/{id}/milestones`, `GET /projects/{id}/ledger`
- [ ] Mock adapter for MX-20, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 6 · Client dashboard and evidence

### WEB-CLIENT-008 · Home: needs your attention

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Uses the generated API client for: `GET /projects`, `GET /projects/{id}/milestones`, `GET /projects/{id}/reports`
- [ ] Mock adapter for MX-02, MX-11, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-009 · Project overview

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id`
- [ ] State: Desktop
- [ ] State: The screen that matters most
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: P2 placeholder only: no form, booking, times or prices. Do not build the feature.
- [ ] Uses the generated API client for: `GET /projects/{id}`, `GET /projects/{id}/milestones`, `GET /projects/{id}/evidence`, `GET /projects/{id}/reports`, `GET /projects/{id}/ledger`
- [ ] Mock adapter for MX-14, MX-20, MX-24, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-010 · Evidence gallery

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id/evidence`
- [ ] State: Gallery
- [ ] State: Empty (filters match nothing)
- [ ] State: Gallery
- [ ] State: Filters sheet
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Rule: A flagged item goes to ops and never rejects a milestone by itself.
- [ ] Uses the generated API client for: `GET /projects/{id}/evidence`
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-011 · Evidence detail

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id/evidence/:evidenceId`
- [ ] State: Accepted supervisor video · UTC shown on hover
- [ ] State: Uploaded by the contractor
- [ ] State: Flagged — as the client sees it
- [ ] State: Accepted
- [ ] State: Under review
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Rule: A flagged item goes to ops and never rejects a milestone by itself.
- [ ] Uses the generated API client for: `GET /projects/{id}/evidence`
- [ ] Mock adapter for MX-07, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-012 · Project site map

- [ ] Built at `web/src/features/dashboard/ + web/src/common/ (map component)` (or the repo's equivalent); route `/projects/:id/site-map`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Uses the generated API client for: `GET /projects/{id}`, `GET /projects/{id}/evidence`
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 7 · Client milestones, money, reports, orders

### WEB-CLIENT-013 · Milestone detail (every state)

- [ ] Built at `web/src/features/milestones/` (or the repo's equivalent); route `/projects/:id/milestones/:milestoneId`
- [ ] State: Pending · Plastering, not funded yet
- [ ] State: Funded · Plastering, work can start
- [ ] State: Claimed · Roofing, waiting for the supervisor
- [ ] State: Verified · Roofing, needs your approval
- [ ] State: Disputed · Roofing, release paused
- [ ] State: Released · Blockwork to Lintel
- [ ] State: Verified
- [ ] State: Pending
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Rule: Status colour appears only in chips and alerts, and every state also differs by text or shape.
- [ ] Uses the generated API client for: `GET /projects/{id}/milestones`, `GET /projects/{id}/evidence`, `GET /projects/{id}/ledger`
- [ ] Mock adapter for MX-07, MX-20, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-014 · Approve a release

- [ ] Built at `web/src/features/milestones/` (or the repo's equivalent); route `/projects/:id/milestones/:milestoneId/approve`
- [ ] State: 1 · Home: the approval card
- [ ] State: 2 · Review
- [ ] State: 3 · Confirm
- [ ] State: Pending release
- [ ] State: Released · receipt
- [ ] State: Confirm dialog
- [ ] State: Released, with receipt
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Rule: Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- [ ] Uses the generated API client for: `POST /milestones/{id}/approve`, `GET /projects/{id}/milestones`, `GET /projects/{id}/ledger`
- [ ] Mock adapter for MX-22, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-015 · Raise a dispute and outcomes

- [ ] Built at `web/src/features/milestones/` (or the repo's equivalent); route `/projects/:id/milestones/:milestoneId/dispute`
- [ ] State: Raise a dispute
- [ ] State: Release paused
- [ ] State: Outcome A · released
- [ ] State: Outcome B · rework required
- [ ] State: Raise a dispute
- [ ] State: Milestone with release paused
- [ ] State: Dispute page, both outcomes
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Uses the generated API client for: `POST /milestones/{id}/disputes`, `GET /projects/{id}/milestones`
- [ ] Mock adapter for MX-10, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-016 · Fund the next milestone

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id/fund/:milestoneId`
- [ ] State: Fund Plastering · Mon 14 Dec
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Fees, prices and rates on this screen are PLACEHOLDER figures until week-one interviews and the escrow partner confirm them.
- [ ] Uses the generated API client for: `POST /projects/{id}/funding`, `GET /projects/{id}/milestones`
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-017 · Ledger

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id/ledger`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Uses the generated API client for: `GET /projects/{id}/ledger`
- [ ] Mock adapter for MX-22, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-018 · Weekly reports

- [ ] Built at `web/src/features/reports/` (or the repo's equivalent); route `/projects/:id/reports, /projects/:id/reports/:reportId`
- [ ] State: List
- [ ] State: List
- [ ] State: Report viewer
- [ ] State: Report viewer
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Uses the generated API client for: `GET /projects/{id}/reports`
- [ ] Mock adapter for MX-13, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-019 · Material orders

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/projects/:id/orders`
- [ ] State: Approve an order · Tue 15 Dec
- [ ] State: Orders and delivery confirmation · Fri 18 Dec
- [ ] State: Approve an order
- [ ] State: Delivery status
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Uses the generated API client for: `POST /orders/{id}/approve`, `POST /quotes/check`, `GET /price-index`
- [ ] Mock adapter for MX-05, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-020 · Notifications

- [ ] Built at `web/src/features/dashboard/ (no notifications feature on web in the Spec)` (or the repo's equivalent); route `/notifications`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Mock adapter for MX-11, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-021 · Live walkthrough (coming soon)

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/projects/:id/walkthrough`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: P2 placeholder only: no form, booking, times or prices. Do not build the feature.
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-022 · Land and title verification (coming soon)

- [ ] Built at `web/src/features/dashboard/` (or the repo's equivalent); route `/add-ons/land-verification`
- [ ] State: Add-on placeholder (FR-22, P2)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: P2 placeholder only: no form, booking, times or prices. Do not build the feature.
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 8 · Contractor

### WEB-CONTRACTOR-003 · Projects dashboard

- [ ] Built at `web/src/features/projects/ (contractor views; no contractor feature folder in the Spec)` (or the repo's equivalent); route `/c`
- [ ] State: Desktop
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Uses the generated API client for: `GET /projects`, `GET /projects/{id}/milestones`
- [ ] Mock adapter for MX-02, MX-06, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-004 · BoQ editor

- [ ] Built at `web/src/features/projects/ (BoQ editor)` (or the repo's equivalent); route `/c/projects/:id/boq`
- [ ] State: Editing version 2 · validation errors · Wed 6 Jan
- [ ] State: Sent back · Sat 2 Jan
- [ ] State: Submitted · in review · Tue 29 Dec
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Uses the generated API client for: `GET /projects/{id}/boq`, `PUT /projects/{id}/boq`, `POST /projects/{id}/boq/approve`, `POST /quotes/check`
- [ ] Mock adapter for MX-08, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-005 · Milestones and claim

- [ ] Built at `web/src/features/milestones/` (or the repo's equivalent); route `/c/projects/:id/milestones`
- [ ] State: Milestone list · Plastering ready to claim
- [ ] State: Claim confirmation
- [ ] State: Claimed · waiting for the supervisor
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Rule: Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Uses the generated API client for: `GET /projects/{id}/milestones`, `POST /milestones/{id}/claim`
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-006 · Rework and dispute

- [ ] Built at `web/src/features/milestones/` (or the repo's equivalent); route `/c/projects/:id/milestones/:milestoneId`
- [ ] State: Rejected with reasons · Wed 6 Jan
- [ ] State: Reworked · claim again · Mon 11 Jan
- [ ] State: Or instead: dispute the rejection · Thu 7 Jan
- [ ] State: Dispute open
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Uses the generated API client for: `GET /projects/{id}/milestones`, `POST /milestones/{id}/claim`, `POST /milestones/{id}/disputes`
- [ ] Mock adapter for MX-10, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-007 · Material requests

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/c/orders`
- [ ] State: New request · Thu 7 Jan
- [ ] State: Orders · statuses
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Uses the generated API client for: `POST /projects/{id}/orders`, `GET /price-index`, `POST /quotes/check`
- [ ] Mock adapter for MX-05, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-008 · Payouts

- [ ] Built at `web/src/features/dashboard/ (no payouts feature on web in the Spec)` (or the repo's equivalent); route `/c/payouts`
- [ ] State: Desktop
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Mock adapter for MX-03, MX-06, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-009 · Profile and track record

- [ ] Built at `web/src/features/auth/ (profile)` (or the repo's equivalent); route `/c/profile`
- [ ] State: Desktop
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, MX-23, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-002 · Projects and claim (Android)

- [ ] Built at `mobile/lib/features/projects/ + mobile/lib/features/milestones/` (or the repo's equivalent); route `ProjectsScreen, MilestoneScreen`
- [ ] State: Projects · Mon 4 Jan
- [ ] State: Milestone · ready to claim
- [ ] State: Claim confirmation
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Rule: Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- [ ] Uses the generated API client for: `GET /projects`, `GET /projects/{id}/milestones`, `POST /milestones/{id}/claim`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-003 · Contractor capture

- [ ] Built at `mobile/lib/features/capture/` (or the repo's equivalent); route `CaptureScreen (contractor mode)`
- [ ] State: Camera · contractor evidence
- [ ] State: After the shot · saved, waiting to upload
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: Contractor uploads are labelled "Uploaded by the contractor" and never count toward supervisor verification.
- [ ] Rule: The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Uses the generated API client for: `POST /evidence/upload-url`, `POST /evidence`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-004 · Orders (Android)

- [ ] Built at `mobile/lib/features/orders/ (new folder; not in the Spec)` (or the repo's equivalent); route `OrdersScreen`
- [ ] State: Orders · Thu 7 Jan
- [ ] Loading, empty and error states use the shared patterns
- [ ] Uses the generated API client for: `POST /projects/{id}/orders`
- [ ] Mock adapter for MX-05, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-005 · Alerts (Android)

- [ ] Built at `mobile/lib/features/notifications/ (new folder; not in the Spec)` (or the repo's equivalent); route `AlertsScreen`
- [ ] State: Alerts · Wed 6 Jan
- [ ] Loading, empty and error states use the shared patterns
- [ ] Mock adapter for MX-11, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 9 · Supervisor Android app

### AND-SUPERVISOR-004 · Assigned projects and checklist

- [ ] Built at `mobile/lib/features/projects/` (or the repo's equivalent); route `ProjectsScreen, ProjectDetailScreen, ChecklistScreen`
- [ ] State: Assigned projects · Wed 6 Jan, 08:40
- [ ] State: Project detail
- [ ] State: Milestone checklist
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Uses the generated API client for: `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/milestones`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-005 · Arrival check

- [ ] Built at `mobile/lib/features/capture/` (or the repo's equivalent); route `ArrivalScreen`
- [ ] State: Finding your location
- [ ] State: Inside the site boundary
- [ ] State: Outside the site boundary
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- [ ] Uses the generated API client for: `GET /projects/{id}`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-006 · Capture

- [ ] Built at `mobile/lib/features/capture/` (or the repo's equivalent); route `CaptureScreen, CaptureReviewScreen`
- [ ] State: Ready to capture
- [ ] State: Refused · GPS too weak
- [ ] State: Refused · mock location
- [ ] State: Warning · capturing outside site
- [ ] State: Review and notes
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: The server decides geofence results (25 m tolerance). The app refuses capture if GPS accuracy is worse than 50 m or the location is mocked, and only warns about the boundary.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Uses the generated API client for: `POST /evidence/upload-url`, `POST /evidence`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-007 · Sync queue

- [ ] Built at `mobile/lib/features/sync/` (or the repo's equivalent); route `SyncScreen`
- [ ] State: Sync queue · online · Wed 6 Jan, 15:45
- [ ] State: Offline · 48-hour warning · Fri 8 Jan, 08:10
- [ ] State: Retry states
- [ ] State: Rejected capture · reason
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Rule: A flagged item goes to ops and never rejects a milestone by itself.
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Uses the generated API client for: `POST /evidence/upload-url`, `POST /evidence`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-008 · Verify or send back

- [ ] Built at `mobile/lib/features/milestones/` (or the repo's equivalent); route `VerifyScreen`
- [ ] State: Verify · re-check Tue 12 Jan
- [ ] State: Send back with reasons · Wed 6 Jan
- [ ] State: Confirm verification
- [ ] State: Conflict · changed while offline
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Uses the generated API client for: `POST /milestones/{id}/verify`, `GET /projects/{id}/milestones`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-009 · Confirm delivery

- [ ] Built at `mobile/lib/features/deliveries/ (new folder; not in the Spec)` (or the repo's equivalent); route `DeliveryScreen`
- [ ] State: Delivery to confirm · Fri 18 Dec, 12:15
- [ ] State: Count and photograph
- [ ] State: Delivery confirmed
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Uses the generated API client for: `POST /orders/{id}/delivery`, `POST /evidence/upload-url`, `POST /evidence`
- [ ] Mock adapter for MX-05, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-010 · Spot checks

- [ ] Built at `mobile/lib/features/spot_checks/` (or the repo's equivalent); route `SpotChecksScreen`
- [ ] State: Spot checks · Thu 7 Jan, 09:00
- [ ] State: Complete with findings
- [ ] State: Findings submitted
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Uses the generated API client for: `GET /supervisors/me/spot-checks`, `POST /spot-checks/{id}/complete`, `POST /evidence/upload-url`, `POST /evidence`
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-011 · Weekly report review

- [ ] Built at `mobile/lib/features/reports/ (new folder; not in the Spec)` (or the repo's equivalent); route `ReportReviewScreen`
- [ ] State: Read the AI draft · Fri 8 Jan, 16:10
- [ ] State: Edit the draft
- [ ] State: Mark reviewed
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Uses the generated API client for: `GET /projects/{id}/reports`, `POST /reports/{id}/review`
- [ ] Mock adapter for MX-13, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-012 · Me, device and system states

- [ ] Built at `mobile/lib/features/auth/ (profile)` (or the repo's equivalent); route `MeScreen`
- [ ] State: Me · profile, vetting, device
- [ ] State: Storage low
- [ ] State: Session expired
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Uses the generated API client for: `GET /supervisors/me/profile`, `POST /devices/{id}/revoke`
- [ ] Mock adapter for MX-12, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 10 · Supplier portal

### WEB-SUPPLIER-002 · Supplier dashboard

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/s`
- [ ] State: Mon 11 Jan 2027, 09:00 WAT
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Mock adapter for MX-05, MX-06, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-003 · Incoming orders

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/s/orders`
- [ ] State: Incoming orders
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Mock adapter for MX-05, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-004 · Order detail, delivery and payment

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/s/orders/:orderId`
- [ ] State: Approved, to deliver
- [ ] State: Delivered, confirmed and paid
- [ ] State: On hold
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supplier is paid directly only after the supervisor confirms the delivery on site.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Mock adapter for MX-05, MX-06, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-005 · Payouts history

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/s/payouts`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Mock adapter for MX-06, MX-22, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-006 · Business profile and bank

- [ ] Built at `web/src/features/suppliers/` (or the repo's equivalent); route `/s/profile`
- [ ] State: Desktop
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, MX-03, MX-04, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-007 · Price list contribution

- [ ] Built at `web/src/features/suppliers/ (price index)` (or the repo's equivalent); route `/s/prices`
- [ ] State: Mon 11 Jan
- [ ] State: Mobile web
- [ ] Loading, empty and error states use the shared patterns
- [ ] Uses the generated API client for: `GET /price-index`
- [ ] Mock adapter for MX-16, logged as a gap
- [ ] Responsive: matches the desktop, mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WA-SUPPLIER-001 · WhatsApp order notification

- [ ] Built at `backend/app/base/notifications/ (templates)` (or the repo's equivalent); route `template: supplier_new_order, supplier_paid`
- [ ] State: WhatsApp chat (mock)
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Responsive: matches the whatsapp frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 11 · Ops console

### WEB-OPS-002 · Overview, live map and money alerts

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops`
- [ ] State: Overview · Mon 11 Jan 2027, 09:30 WAT
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Uses the generated API client for: `GET /ops/queue`, `GET /projects`
- [ ] Mock adapter for MX-21, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-003 · Supervisor vetting

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/vetting, /ops/vetting/:id`
- [ ] State: Vetting queue
- [ ] State: Vetting detail · decide
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Uses the generated API client for: `GET /ops/queue`, `POST /supervisors/{id}/vetting`
- [ ] Mock adapter for MX-15, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-004 · Projects, BoQ approval and rotation

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/projects, /ops/projects/:id`
- [ ] State: Projects list
- [ ] State: Project detail · pause, site, supervisor rotation
- [ ] State: BoQ ops approval · Emeka's duplex v2
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Rule: The client can set or change the site only in draft or boq_review (409 site_locked after); the pin must be inside the polygon (422 pin_outside_geofence).
- [ ] Rule: BoQ line totals are computed by the server (422 boq_total_mismatch on mismatch); funding opens only after client, contractor and ops approve; the final approval needs a saved site (409 site_not_set).
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Uses the generated API client for: `GET /projects`, `GET /projects/{id}`, `POST /projects/{id}/supervisor`, `PUT /projects/{id}/site`, `GET /projects/{id}/boq`, `POST /projects/{id}/boq/approve`
- [ ] Mock adapter for MX-08, MX-09, MX-15, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-005 · Flagged evidence review

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/evidence/:id`
- [ ] State: Flagged evidence review
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: A flagged item goes to ops and never rejects a milestone by itself.
- [ ] Rule: Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Uses the generated API client for: `GET /ops/queue`, `POST /evidence/{id}/decision`
- [ ] Mock adapter for MX-07, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-006 · Disputes and two-approver resolution

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/disputes, /ops/disputes/:id`
- [ ] State: Dispute queue
- [ ] State: Resolution · two-approver flow
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Dispute resolution needs two different ops approvers; the first proposes, the second approves.
- [ ] Rule: A release needs BOTH supervisor verification and client approval. A dispute pauses release. No UI action may skip either approval.
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Uses the generated API client for: `GET /ops/queue`, `POST /disputes/{id}/resolve`
- [ ] Mock adapter for MX-10, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-007 · Spot-check scheduler

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/spot-checks`
- [ ] State: Spot-check scheduler and results
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Uses the generated API client for: `POST /projects/{id}/spot-checks`
- [ ] Mock adapter for MX-14, MX-15, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-008 · Supplier verification

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/suppliers`
- [ ] State: Supplier verification and onboarding
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Bank account numbers are masked (******1234); only the last 4 NIN digits are kept after the check.
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Mock adapter for MX-02, MX-03, MX-04, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-009 · Price index management

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/price-index`
- [ ] State: Price index management
- [ ] Loading, empty and error states use the shared patterns
- [ ] Uses the generated API client for: `GET /price-index`
- [ ] Mock adapter for MX-16, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-010 · Weekly report review (ops)

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/reports`
- [ ] State: Weekly report review
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Uses the generated API client for: `GET /projects/{id}/reports`, `POST /reports/{id}/review`
- [ ] Mock adapter for MX-13, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-011 · Audit log and agent runs

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/audit, /ops/agent-runs`
- [ ] State: Audit log
- [ ] State: Agent runs log
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Uses the generated API client for: `GET /ops/audit`
- [ ] Mock adapter for MX-18, MX-22, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-012 · Users and status

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/users`
- [ ] State: User management · role and status
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Rule: Role and project membership are checked on every request; each role sees only its own screens.
- [ ] Mock adapter for MX-17, MX-02, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

## Stage 12 · Cross-cutting: messages, settings, system states

### WA-CLIENT-001 · Client WhatsApp messages

- [ ] Built at `backend/app/base/notifications/ (templates)` (or the repo's equivalent); route `templates: milestone_claimed, milestone_verified, release_completed, weekly_report_ready`
- [ ] State: Client · WhatsApp · Chioma
- [ ] State: Client · WhatsApp · weekly report summary
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Responsive: matches the whatsapp frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-013 · Spot check SMS and push

- [ ] Built at `backend/app/base/notifications/ + mobile push handling` (or the repo's equivalent); route `push + SMS: spot_check_assigned`
- [ ] State: Supervisor · SMS + push · spot check assigned
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### EMAIL-CLIENT-001 · Client emails

- [ ] Built at `backend/app/base/notifications/ (email templates)` (or the repo's equivalent); route `templates: milestone_verified, weekly_report`
- [ ] State: Milestone verified
- [ ] State: Weekly report
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Responsive: matches the email frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-014 · Supervisor push notifications

- [ ] Built at `mobile/lib/core/ (FCM) ` (or the repo's equivalent); route `push templates`
- [ ] State: Supervisor app · notifications
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Spot checks are unannounced: the contractor is never notified; the client sees results only after ops closes them.
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-CONTRACTOR-006 · Contractor push notifications

- [ ] Built at `mobile/lib/core/ (FCM)` (or the repo's equivalent); route `push templates`
- [ ] State: Contractor app · notifications
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WA-CLIENT-002 · WhatsApp assistant

- [ ] Built at `backend/app/features/agents/` (or the repo's equivalent); route `webhook: POST /webhooks/whatsapp`
- [ ] State: WhatsApp assistant · questions it answers
- [ ] State: Read-only boundary · hand-off to ops
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- [ ] Rule: Nothing can be approved, released or paid inside WhatsApp, SMS or email; links open the web app.
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Uses the generated API client for: `POST /webhooks/whatsapp`
- [ ] Responsive: matches the whatsapp frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-023 · Client settings

- [ ] Built at `web/src/features/settings/ (new folder; not in the Spec)` (or the repo's equivalent); route `/settings`
- [ ] State: Client · notifications
- [ ] State: Client · time zone and currency
- [ ] State: Client · data and privacy
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Rule: Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, MX-19, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-010 · Devices and revoke

- [ ] Built at `web/src/features/settings/ (new folder)` (or the repo's equivalent); route `/c/settings/devices`
- [ ] State: Contractor · devices · revoke
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Uses the generated API client for: `POST /devices/{id}/revoke`
- [ ] Mock adapter for MX-12, logged as a gap
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-013 · Ops profile, alerts and security

- [ ] Built at `web/src/features/ops-console/` (or the repo's equivalent); route `/ops/settings`
- [ ] State: Ops · profile, alerts and security
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- [ ] Rule: Every money movement and sensitive action is audit-logged; the audit log is read-only.
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, logged as a gap
- [ ] Responsive: matches the desktop frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-015 · Supervisor settings and revoke

- [ ] Built at `mobile/lib/features/auth/ (settings)` (or the repo's equivalent); route `SettingsScreen`
- [ ] State: Supervisor app · settings
- [ ] State: Supervisor app · revoke old phone
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Captures keep their original time and location offline; uploads must happen within 72 h of capture, with a warning at 48 h.
- [ ] Uses the generated API client for: `POST /devices/{id}/revoke`
- [ ] Mock adapter for MX-01, MX-12, logged as a gap
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-008 · Supplier notification settings

- [ ] Built at `web/src/features/settings/ (new folder)` (or the repo's equivalent); route `/s/settings`
- [ ] State: Supplier · mobile web · notifications
- [ ] Loading, empty and error states use the shared patterns
- [ ] Uses the generated API client for: `GET /me`
- [ ] Mock adapter for MX-01, logged as a gap
- [ ] Responsive: matches the mobile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-024 · System states (web)

- [ ] Built at `web/src/common/ (UI kit: error pages, toasts, dialogs, skeletons)` (or the repo's equivalent); route `(shared states for every web portal)`
- [ ] State: 404 · page not found
- [ ] State: 500 · server error
- [ ] State: Permission denied · 403
- [ ] State: 409 · conflict, already done elsewhere
- [ ] State: Form validation
- [ ] State: Session expired
- [ ] State: Offline
- [ ] State: Loading skeleton
- [ ] State: Success toasts
- [ ] State: Confirmation dialog
- [ ] State: Destructive dialog
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Any invalid state change returns 409; show the conflict state (what changed, nothing done twice) instead of a generic error.
- [ ] Rule: Status colour appears only in chips and alerts, and every state also differs by text or shape.
- [ ] Rule: Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- [ ] Rule: Every write sends an Idempotency-Key; disable the submit button while a write is in flight.
- [ ] Responsive: matches the desktop frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-016 · System states (Android)

- [ ] Built at `mobile/lib/core/ (UI kit)` (or the repo's equivalent); route `(shared app states)`
- [ ] State: Server error
- [ ] State: Location permission denied
- [ ] State: Camera permission denied
- [ ] State: Not allowed · rotated off
- [ ] State: Form validation
- [ ] State: Loading skeleton
- [ ] State: Snackbars
- [ ] State: Confirmation dialog
- [ ] State: Destructive dialog
- [ ] Loading, empty and error states use the shared patterns
- [ ] Rule: Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
- [ ] Rule: A supervisor related to the contractor can never be assigned or spot-check that contractor; supervisors rotate after two consecutive milestones.
- [ ] Rule: Status colour appears only in chips and alerts, and every state also differs by text or shape.
- [ ] Responsive: matches the android frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CLIENT-025 · Empty states (client)

- [ ] Built at `web/src/common/ (empty state component)` (or the repo's equivalent); route `(projects, evidence, reports, ledger, orders, notifications)`
- [ ] State: Client · Projects
- [ ] State: Client · Evidence
- [ ] State: Client · Reports
- [ ] State: Client · Ledger
- [ ] State: Client · Orders
- [ ] State: Client · Notifications
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the tile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-CONTRACTOR-011 · Empty states (contractor)

- [ ] Built at `web/src/common/ (empty state component)` (or the repo's equivalent); route `(projects, payouts, orders)`
- [ ] State: Contractor · Projects
- [ ] State: Contractor · Payouts
- [ ] State: Contractor · Orders
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the tile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### AND-SUPERVISOR-017 · Empty states (supervisor)

- [ ] Built at `mobile/lib/core/ (empty state widget)` (or the repo's equivalent); route `(projects, sync, spot checks)`
- [ ] State: Supervisor · Projects
- [ ] State: Supervisor · Sync
- [ ] State: Supervisor · Spot checks
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the tile frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 48dp targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-SUPPLIER-009 · Empty states (supplier)

- [ ] Built at `web/src/common/ (empty state component)` (or the repo's equivalent); route `(orders, payouts)`
- [ ] State: Supplier · Orders
- [ ] State: Supplier · Payouts
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the tile frames (and works at 390px)
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code

### WEB-OPS-014 · Empty states (ops)

- [ ] Built at `web/src/common/ (empty state component)` (or the repo's equivalent); route `(vetting, disputes)`
- [ ] State: Ops · Vetting
- [ ] State: Ops · Disputes
- [ ] Loading, empty and error states use the shared patterns
- [ ] Responsive: matches the tile frames
- [ ] Accessibility: keyboard/TalkBack, visible focus, 4.5:1 text, labelled controls, 44px targets
- [ ] Uses tokens only (no hard-coded colours); no PLACEHOLDER copy or fixture data in production code
