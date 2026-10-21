# Components

Every component used across the approved screens. Build each once in the existing component library (web) and widget set (Flutter), then reuse it. The visual sheet is [components.html](components.html); tokens are in [tokens.json](tokens.json) / [tokens.css](tokens.css).

"Where it appears" is detected from the approved frames, so treat it as a strong guide, not an exhaustive contract.

## Shared canvas components

These were real shared components on the Design canvas (imported into many boards). Mirror them as shared components with the same props.

| Component | Props | Use |
|---|---|---|
| SiteHeader | active, mobile | Public-site header. |
| SiteFooter | mobile | Public-site footer. |
| AuthCard | state (phone, country, email, otp, otpWrong, otpLocked, otpExpired, rateLimited, channelDown, sendFailed, consent), surface | Sign-in card; every OTP state. |
| ClientTop | project, mobile | Client top bar with notifications bell. |
| ClientTabs | active, msBadge, ordBadge | Project tabs incl. Orders. |
| ClientNav | active | Client mobile bottom nav. |
| MsDetail | state (pending, funded, claimed, verified, released, disputed), mobile | Milestone detail body for all states. |
| ConTop | active, project ("", bungalow, duplex), tab | Contractor top bar. |
| ConAppNav | active | Contractor Android bottom nav. |

## Foundations

### Wordmark

House outline with an eye inside, plus "iBackHome" in Inter 700. Navy square on light backgrounds, white square on navy.

- Variants: on light, on navy, icon only (favicon, app icon)
- States: —
- Usage rules: Never recolour beyond navy/white; keep the clear space of one eye height.
- Where it appears (77): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-PUBLIC-010, AND-PUBLIC-001, WA-CONTRACTOR-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, WEB-SUPPLIER-001, WEB-OPS-001, WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021, WEB-CLIENT-022, WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009, AND-CONTRACTOR-002, AND-SUPERVISOR-004, AND-SUPERVISOR-007, AND-SUPERVISOR-010, AND-SUPERVISOR-012, WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WA-SUPPLIER-001, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WA-CLIENT-001, AND-SUPERVISOR-013, EMAIL-CLIENT-001, AND-SUPERVISOR-014, AND-CONTRACTOR-006, WA-CLIENT-002, WEB-CLIENT-023, WEB-CONTRACTOR-010, WEB-OPS-013, WEB-CLIENT-024, AND-SUPERVISOR-016

## Navigation

### Site header and footer

Public-site top bar (links, Sign in, Get started) and footer.

- Variants: desktop, mobile (menu)
- States: default, active link
- Usage rules: Shared by every public page.
- Where it appears (9): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009

### Client top bar

Wordmark, project switcher, Notifications with badge, Help, initials avatar.

- Variants: desktop 64px, mobile 56px
- States: default, unread badge
- Usage rules: Used on every signed-in client page.
- Where it appears (23): WEB-CLIENT-001, WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021, WEB-CLIENT-022, WEB-CLIENT-023, WEB-CLIENT-024

### Project tabs

Overview, Milestones (badge), Evidence, Reports, Ledger, BoQ, Site map, Orders (badge).

- Variants: desktop
- States: active tab, badge
- Usage rules: Badges count items that need the client.
- Where it appears (8): WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019

### Client bottom nav

Mobile-web bottom bar: Home, Milestones (badge), Evidence, Money, Reports.

- Variants: mobile 72px
- States: active item, badge
- Usage rules: 44px targets; the active item also differs by weight, not colour alone.
- Where it appears (11): WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-012, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021

### Contractor top bar

Contractor portal bar: Projects, Orders, Payouts, Profile, plus project context row.

- Variants: desktop
- States: active item, with or without project row
- Where it appears (8): WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009, WEB-CONTRACTOR-010

### Contractor app bottom nav

Android bottom bar for contractors.

- Variants: android 360
- States: active item, badge
- Usage rules: 48dp targets.
- Where it appears (3): AND-CONTRACTOR-002, AND-CONTRACTOR-004, AND-CONTRACTOR-005

### Supplier top bar and mobile nav

Supplier portal: Dashboard, Orders, Payouts, Price list, Profile; mobile bottom nav.

- Variants: desktop, mobile
- States: active item, badge
- Where it appears (6): WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007

### Ops sidebar

Ops console left navigation: Queues (Vetting, Flagged evidence, Disputes), Operations, Records; signed-in person and session time.

- Variants: desktop 1440 only
- States: active item, count badges
- Usage rules: Desktop only. Session time left is always visible.
- Where it appears (11): WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012

### Android app bar and bottom nav

Supervisor app: top app bar with back/close and subtitle; bottom nav (Projects, Spot checks, Sync, Me).

- Variants: android 360×800
- States: default, offline banner, sync badge
- Usage rules: 48dp targets; title 18/24, body 15/22 minimum.
- Where it appears (11): AND-SUPERVISOR-004, AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-011, AND-SUPERVISOR-012, AND-SUPERVISOR-015, AND-SUPERVISOR-016

## Controls

### Buttons

Primary (navy), secondary (mist or white with border), tertiary (outlined/text), destructive (red, only inside dialogs).

- Variants: web 44–48px, android 48dp; full-width on mobile
- States: default, hover, focus, pressed, disabled, loading
- Usage rules: One primary per view. Destructive buttons appear only inside a confirmation dialog, with the safe choice on the left.
- Where it appears (78): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-PUBLIC-010, AND-PUBLIC-001, WEB-CONTRACTOR-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-SUPPLIER-001, AND-SUPERVISOR-001, AND-SUPERVISOR-002, WEB-OPS-001, WEB-CLIENT-002, AND-SUPERVISOR-003, WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-010, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021, WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, AND-CONTRACTOR-002, AND-CONTRACTOR-003, AND-CONTRACTOR-004, AND-SUPERVISOR-004, AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-011, AND-SUPERVISOR-012, WEB-SUPPLIER-002, WEB-SUPPLIER-004, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, EMAIL-CLIENT-001, WEB-CLIENT-023, WEB-CONTRACTOR-010, AND-SUPERVISOR-015, WEB-SUPPLIER-008, WEB-CLIENT-024, AND-SUPERVISOR-016, WEB-CLIENT-025, WEB-CONTRACTOR-011, WEB-SUPPLIER-009, WEB-OPS-014

### Text input and select

Labelled field with helper and error text; select with chevron.

- Variants: default, compact (ops)
- States: default, focus, filled, error, disabled, read-only
- Usage rules: Labels are always visible; errors say what to do and use red only for border and helper text.
- Where it appears (27): WEB-PUBLIC-007, WEB-PUBLIC-010, AND-PUBLIC-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, WEB-SUPPLIER-001, WEB-OPS-001, WEB-CLIENT-003, WEB-CLIENT-005, WEB-CONTRACTOR-004, AND-SUPERVISOR-006, AND-SUPERVISOR-008, AND-SUPERVISOR-010, AND-SUPERVISOR-011, WEB-SUPPLIER-007, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WEB-CLIENT-023, WEB-CLIENT-024, AND-SUPERVISOR-016

### OTP code input

Six single-digit boxes with countdown, resend after 30 s, switch channel.

- Variants: web, android
- States: empty, typing, error, expired, locked after 5 attempts
- Usage rules: Paste of a 6-digit code fills all boxes; announce errors to screen readers.
- Where it appears (2): WEB-PUBLIC-010, AND-PUBLIC-001

### Segmented control and tabs

Inline switch between views (filters, roles, photo/video).

- Variants: web, android
- States: selected, focus
- Where it appears (10): WEB-PUBLIC-010, AND-PUBLIC-001, WEB-CLIENT-017, AND-SUPERVISOR-006, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-006, WEB-OPS-009, WEB-OPS-012

### Toggle, checkbox and radio card

Settings switches, checklist ticks, choice cards.

- Variants: web, android
- States: on, off, disabled, focus
- Usage rules: Every toggle has a visible text label.
- Where it appears (5): WEB-PUBLIC-007, WEB-CLIENT-023, WEB-OPS-013, AND-SUPERVISOR-015, WEB-SUPPLIER-008

### Search and filters

Search field and filter chips/sheet (evidence gallery, ops lists).

- Variants: desktop bar, mobile sheet
- States: empty, active filters, no results
- Where it appears (12): WEB-CLIENT-010, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012

## Feedback

### Status chip

Pill with text (and icon where needed) in one of five tones: ok, warn, bad, neutral, info.

- Variants: small 24px, default 26px
- States: one per state (see 04-api-mapping/state-to-ui.md)
- Usage rules: The only place status colour appears besides alerts. Text always names the state.
- Where it appears (76): WEB-PUBLIC-001, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-CONTRACTOR-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-SUPPLIER-001, AND-SUPERVISOR-001, AND-SUPERVISOR-002, WEB-OPS-001, WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021, WEB-CLIENT-022, WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009, AND-CONTRACTOR-002, AND-CONTRACTOR-004, AND-CONTRACTOR-005, AND-SUPERVISOR-004, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-011, AND-SUPERVISOR-012, WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, EMAIL-CLIENT-001, WEB-CLIENT-023, WEB-CONTRACTOR-010, AND-SUPERVISOR-015, WEB-CLIENT-024, WEB-CLIENT-025, WEB-CONTRACTOR-011, AND-SUPERVISOR-017, WEB-SUPPLIER-009, WEB-OPS-014

### Alert and banner

Inline message with icon; tinted background and a 4px left edge for warn, bad and ok; neutral mist for info.

- Variants: inline, page banner, offline bar
- States: ok, warn, bad, neutral
- Usage rules: Use role="alert" for warn and bad, role="status" otherwise.
- Where it appears (27): WEB-CLIENT-013, WEB-CLIENT-015, WEB-CLIENT-019, WEB-CONTRACTOR-004, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-012, WEB-SUPPLIER-004, WEB-SUPPLIER-007, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WEB-CLIENT-024, AND-SUPERVISOR-016

### Toast and snackbar

Short confirmation of something that already happened; navy surface.

- Variants: web toast (bottom right), android snackbar
- States: success, with action, dismissible
- Usage rules: Stays 6 s (longer on hover), never the only record of an important event.
- Where it appears (2): WEB-CLIENT-024, AND-SUPERVISOR-016

### Skeleton loader

Grey blocks matching the real layout, gentle pulse (no shimmer).

- Variants: web, android
- States: loading, slow (after [10 s] says it is taking longer)
- Where it appears (3): WEB-CLIENT-006, WEB-CLIENT-024, AND-SUPERVISOR-016

### Empty state

Icon, one-line reason the list is empty, and a button only when the person can act.

- Variants: card, full page
- States: —
- Where it appears (8): WEB-CLIENT-001, WEB-CLIENT-003, WEB-CLIENT-010, WEB-CLIENT-025, WEB-CONTRACTOR-011, AND-SUPERVISOR-017, WEB-SUPPLIER-009, WEB-OPS-014

### Error page

404, 500, 403 and 409 conflict pages with what happened, whether money was affected, and what to do next.

- Variants: web, android
- States: 404, 500, 403, 409
- Usage rules: Never show only a code.
- Where it appears (2): WEB-CLIENT-024, AND-SUPERVISOR-016

## Overlays

### Dialog and alert dialog

Centred dialog for confirmations; alert dialog for destructive or money actions.

- Variants: web, android
- States: open, focus trapped
- Usage rules: Focus moves in and returns to the trigger; Escape closes everything except an alert dialog about money.
- Where it appears (17): WEB-CONTRACTOR-001, WEB-OPS-001, WEB-CLIENT-002, AND-SUPERVISOR-003, WEB-CLIENT-005, WEB-CLIENT-010, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, AND-CONTRACTOR-002, AND-SUPERVISOR-008, AND-SUPERVISOR-011, WEB-CONTRACTOR-010, AND-SUPERVISOR-015, WEB-CLIENT-024, AND-SUPERVISOR-016

### Bottom sheet and side panel

Mobile bottom sheet (filters, session expired) and desktop side panel.

- Variants: mobile, android, desktop
- States: open, dragging
- Where it appears (6): WEB-CLIENT-002, WEB-CLIENT-010, AND-SUPERVISOR-008, AND-SUPERVISOR-011, AND-SUPERVISOR-015, AND-SUPERVISOR-016

## Money

### Money display

Client-currency amount first, then NGN and the rate with its date (for example "£6,800.00 · ₦13,260,000 · £1 = ₦1,950.00").

- Variants: large (cards), inline, table cell
- States: estimate (≈) before funding, fixed after
- Usage rules: Contractors, suppliers and supervisors see NGN only. Tabular figures.
- Where it appears (18): WEB-PUBLIC-001, WEB-CLIENT-005, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WA-CLIENT-001, EMAIL-CLIENT-001, WA-CLIENT-002, WEB-CLIENT-023, WEB-CLIENT-024

### Escrow trust line

Lock icon + "Held by a licensed escrow partner, never by iBackHome."

- Variants: inline, card footer, message footer
- States: —
- Usage rules: Required wherever money is shown, held or moved.
- Where it appears (45): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-PUBLIC-010, WEB-CLIENT-001, WEB-CLIENT-003, WEB-CLIENT-005, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CONTRACTOR-003, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, AND-CONTRACTOR-004, AND-SUPERVISOR-009, AND-SUPERVISOR-011, WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WA-SUPPLIER-001, WEB-OPS-004, WEB-OPS-006, WEB-OPS-010, WA-CLIENT-001, EMAIL-CLIENT-001, AND-CONTRACTOR-006, WA-CLIENT-002, WEB-CLIENT-024

### Escrow balance card

"In escrow now" amount with funding date and rate.

- Variants: desktop aside, mobile card
- States: funded, nothing held
- Where it appears (4): WEB-CLIENT-009, WEB-CLIENT-017, WEB-CLIENT-019, WEB-CONTRACTOR-008

### Spend vs budget bar

Released / in escrow / not funded segments against the budget.

- Variants: desktop, mobile
- States: under budget, over budget
- Usage rules: Segments differ by pattern and label, not colour alone.
- Where it appears (1): WEB-CLIENT-009

### Ledger row and receipt

Ledger table rows with reference, account, amount, currency and rate; release receipt.

- Variants: table, mobile list, receipt card
- States: funding, release, payout, fee
- Where it appears (16): WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CONTRACTOR-005, WEB-CONTRACTOR-008, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WA-SUPPLIER-001, WEB-OPS-002, WEB-OPS-011, WA-CLIENT-001, WEB-CLIENT-024

## Milestones and evidence

### Milestone stepper

Five nodes: released/approved navy fill + check, verified accent ring + check, claimed amber ring + hand, funded navy ring + lock, pending dashed ring + number, disputed red ring + scales.

- Variants: horizontal (desktop), vertical (mobile)
- States: pending, funded, claimed, verified, approved, released, disputed
- Usage rules: Each node differs by icon and label, not colour alone.
- Where it appears (8): WEB-CONTRACTOR-002, WEB-CLIENT-005, WEB-CLIENT-009, WEB-CLIENT-018, WEB-CONTRACTOR-005, WEB-CONTRACTOR-008, AND-SUPERVISOR-004, WEB-OPS-004

### Milestone detail panel (MsDetail)

Two-key release panel, checklist with evidence, money, people and activity for one milestone.

- Variants: desktop, mobile
- States: pending, funded, claimed, verified, disputed, released
- Usage rules: Release needs both keys; the approve action exists only in the verified state.
- Where it appears (3): WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015

### Evidence card

Thumbnail, status chip, title, time and who captured it; contractor uploads carry an outlined "Contractor" label.

- Variants: grid card, strip card, list row
- States: accepted, under review (flagged), rejected, contractor upload
- Usage rules: Contractor uploads never count toward verification.
- Where it appears (23): WEB-PUBLIC-001, WEB-OPS-001, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CONTRACTOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-011, WEB-SUPPLIER-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-010, WEB-OPS-011, AND-SUPERVISOR-014, WA-CLIENT-002, AND-SUPERVISOR-016

### Three-checks list

Inside the site boundary · Signed on the registered phone · Not reused or edited, each with a pass/fail icon and detail.

- Variants: full list, compact chips
- States: pass, fail, under review
- Usage rules: Same three checks, same order, same words wherever evidence appears.
- Where it appears (9): WEB-PUBLIC-001, WEB-PUBLIC-006, WEB-CLIENT-011, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-019, AND-SUPERVISOR-007, EMAIL-CLIENT-001

### Geofence map

Site boundary polygon (navy 2px, 8% fill), dashed 25 m tolerance band, site pin, capture points.

- Variants: large, mini (evidence detail), Android arrival
- States: drawing, saved, locked, pin outside (error)
- Usage rules: The map is never the only way to read a result: inside/outside is also written.
- Where it appears (6): WEB-PUBLIC-001, WEB-CLIENT-004, WEB-CLIENT-011, WEB-CLIENT-012, AND-SUPERVISOR-005, WEB-OPS-004

### Checklist row

Required capture item with evidence IDs and count, or "Not captured / Required".

- Variants: web, android
- States: required, captured, accepted, rejected
- Where it appears (14): WEB-PUBLIC-002, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-018, WEB-CONTRACTOR-003, WEB-CONTRACTOR-006, AND-SUPERVISOR-004, AND-SUPERVISOR-006, AND-SUPERVISOR-007, WEB-OPS-005, EMAIL-CLIENT-001

### Camera and capture bar

In-app camera with geofence bar (inside/outside), GPS accuracy, device key and clock pills, photo/video switch and shutter.

- Variants: android
- States: ready, refused (weak GPS, mock location), warning (outside)
- Usage rules: There is no gallery or file-picker button anywhere.
- Where it appears (2): AND-CONTRACTOR-003, AND-SUPERVISOR-006

### Sync row

Queued capture with thumbnail and state: queued, uploading, accepted, flagged, rejected with reason, retrying.

- Variants: android
- States: queued, uploading, accepted, flagged, rejected, retrying
- Usage rules: Show the 48 h warning before the 72 h upload window ends.
- Where it appears (3): AND-SUPERVISOR-003, AND-SUPERVISOR-006, AND-SUPERVISOR-007

## AI and reports

### AI-generated label

Small "AI-generated" tag (sparkles icon) on any AI output, with cited evidence IDs.

- Variants: chip, inline
- States: —
- Usage rules: Always present on AI output; never on human decisions.
- Where it appears (11): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-005, WEB-PUBLIC-009, WEB-CLIENT-009, WEB-CLIENT-018, WEB-CLIENT-020, AND-SUPERVISOR-011, WEB-OPS-010, WA-CLIENT-001, EMAIL-CLIENT-001

### Reviewed-by badge

"Reviewed by <supervisor>" next to the AI label on reports.

- Variants: chip
- States: reviewed, not reviewed
- Where it appears (11): WEB-PUBLIC-001, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-018, WEB-CLIENT-020, AND-SUPERVISOR-011, WEB-OPS-010, WA-CLIENT-001, EMAIL-CLIENT-001

### Quote check result

Flagged lines first with index price and % difference; "advisory" note that rules, not the AI, decide flags.

- Variants: table, mobile list
- States: checking, results, nothing flagged
- Where it appears (12): WEB-PUBLIC-008, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CONTRACTOR-004, WEB-CONTRACTOR-007, WEB-SUPPLIER-007, WEB-OPS-004, WEB-OPS-008, WEB-OPS-009, WEB-OPS-011

## Placeholders

### Coming soon placeholder

Dashed card with "Coming soon" chip, short description and links to what works today.

- Variants: card, page
- States: —
- Usage rules: P2 only. No form, times or prices.
- Where it appears (4): WEB-PUBLIC-003, WEB-CLIENT-009, WEB-CLIENT-021, WEB-CLIENT-022

## Messages

### WhatsApp message

Business-account chat bubble with buttons that open the web app; template copy.

- Variants: phone mock 390
- States: template, reply
- Usage rules: Nothing is approved inside WhatsApp; Meta-approved templates outside 24 h.
- Where it appears (4): WA-CONTRACTOR-001, WA-SUPPLIER-001, WA-CLIENT-001, WA-CLIENT-002

### Email template

Plain one-column email: brand, heading, both currencies, escrow line, one primary button, preferences link.

- Variants: email 680
- States: —
- Where it appears (1): EMAIL-CLIENT-001

### Push and SMS notification

Android notification shade entries and SMS copy.

- Variants: android
- States: —
- Usage rules: Spot-check SMS omits the client name and exact address.
- Where it appears (3): AND-SUPERVISOR-013, AND-SUPERVISOR-014, AND-CONTRACTOR-006

## Data display

### Table

Dense data table with scope="col" headers (ops console, ledger, BoQ, payouts).

- Variants: desktop; becomes a list on mobile
- States: default, row highlight, empty
- Usage rules: Ops tables use 13/19 type; money columns right-aligned with tabular figures.
- Where it appears (25): WEB-CLIENT-005, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CONTRACTOR-004, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-007, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WEB-CLIENT-023, WEB-CONTRACTOR-010, WEB-OPS-013, WEB-SUPPLIER-008

### Card

White card, 12px radius, 1px line border, subtle shadow.

- Variants: default, padded, inset list
- States: —
- Where it appears (93): WEB-PUBLIC-001, WEB-PUBLIC-002, WEB-PUBLIC-003, WEB-PUBLIC-004, WEB-PUBLIC-005, WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009, WEB-PUBLIC-010, WEB-CONTRACTOR-001, WEB-CLIENT-001, WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-SUPPLIER-001, AND-SUPERVISOR-001, AND-SUPERVISOR-002, WEB-OPS-001, AND-SUPERVISOR-003, WEB-CLIENT-003, WEB-CLIENT-004, WEB-CLIENT-005, WEB-CLIENT-006, WEB-CLIENT-007, WEB-CLIENT-008, WEB-CLIENT-009, WEB-CLIENT-010, WEB-CLIENT-011, WEB-CLIENT-012, WEB-CLIENT-013, WEB-CLIENT-014, WEB-CLIENT-015, WEB-CLIENT-016, WEB-CLIENT-017, WEB-CLIENT-018, WEB-CLIENT-019, WEB-CLIENT-020, WEB-CLIENT-021, WEB-CLIENT-022, WEB-CONTRACTOR-003, WEB-CONTRACTOR-004, WEB-CONTRACTOR-005, WEB-CONTRACTOR-006, WEB-CONTRACTOR-007, WEB-CONTRACTOR-008, WEB-CONTRACTOR-009, AND-CONTRACTOR-002, AND-CONTRACTOR-003, AND-CONTRACTOR-004, AND-SUPERVISOR-004, AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007, AND-SUPERVISOR-008, AND-SUPERVISOR-009, AND-SUPERVISOR-010, AND-SUPERVISOR-011, AND-SUPERVISOR-012, WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WA-CLIENT-001, AND-SUPERVISOR-013, EMAIL-CLIENT-001, AND-SUPERVISOR-014, AND-CONTRACTOR-006, WA-CLIENT-002, WEB-CLIENT-023, WEB-CONTRACTOR-010, WEB-OPS-013, AND-SUPERVISOR-015, WEB-SUPPLIER-008, WEB-CLIENT-024, AND-SUPERVISOR-016, WEB-CLIENT-025, WEB-CONTRACTOR-011, AND-SUPERVISOR-017, WEB-SUPPLIER-009, WEB-OPS-014

### Avatar (initials)

Circular initials avatar for people.

- Variants: 24, 32, 40px
- States: —
- Usage rules: Always paired with the full name.
- Where it appears (21): WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004, WEB-SUPPLIER-005, WEB-SUPPLIER-006, WEB-SUPPLIER-007, WEB-OPS-002, WEB-OPS-003, WEB-OPS-004, WEB-OPS-005, WEB-OPS-006, WEB-OPS-007, WEB-OPS-008, WEB-OPS-009, WEB-OPS-010, WEB-OPS-011, WEB-OPS-012, WEB-CLIENT-023, WEB-CONTRACTOR-010, WEB-OPS-013, WEB-CLIENT-024

## Global rules

- Money shows the client currency first, then the NGN amount and the FX rate recorded for that transaction. Contractors, suppliers and supervisors see NGN only.
- Wherever money is shown, held or moved, show "Held by a licensed escrow partner, never by iBackHome."
- Wherever evidence appears, show the same three checks: inside the site geofence, device-signed, not reused or edited.
- Status colour appears only in chips and alerts, and every state also differs by text or shape.
- AI output is labelled "AI-generated", cites the evidence IDs it used, and never approves, releases or pays. Money figures come from the ledger.
- Times are stored in UTC and shown in the viewer's time zone (clients: their own zone with UTC on hover; Nigerian roles: WAT).
- Capture is in-app camera only. There is no gallery, file picker or share-in path anywhere in the app.
