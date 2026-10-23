# Product summary

Condensed from the PRD (Draft v0.1, 7 Oct 2026). The PRD and the Spec stay the source of truth; this page only orients a reader.

**iBackHome** (said "eyes back home") lets Nigerians abroad build homes in Nigeria with confidence. Verified supervisors capture site evidence that can't be faked, and money is released milestone by milestone through a licensed escrow partner only after a supervisor verifies the work and the client approves it. iBackHome is not a construction company and never holds client funds.

- Tagline: **Far from home, never out of sight.**
- Supporting line: **Proof, not promises.**

## Roles and surfaces

| Role | Who | What they do | Surface (package ID prefix) |
|---|---|---|---|
| Client abroad | Nigerian in the UK, US, Canada or Europe building at home in Nigeria; the payer and primary user | Sets up the project, funds milestones, approves releases, reads reports | React web, mobile-web first for approvals (WEB-CLIENT), WhatsApp and email (WA-CLIENT, EMAIL-CLIENT) |
| Contractor | Builder hired by the client | Submits the BoQ, claims milestones, requests materials | React web portal (WEB-CONTRACTOR), Flutter Android (AND-CONTRACTOR) |
| Supervisor | Registered builder or engineer (COREN or NIOB) vetted by iBackHome | Visits, captures evidence, verifies milestones, confirms deliveries, spot checks | Flutter Android only, offline-first, Android 8+, 2 GB RAM (AND-SUPERVISOR) |
| Supplier | Verified seller of materials | Receives orders, delivers, gets paid directly | React web portal (WEB-SUPPLIER), WhatsApp (WA-SUPPLIER) |
| Operations | iBackHome staff | Vets supervisors and suppliers, schedules spot checks, rotates supervisors, resolves disputes | React admin console, desktop (WEB-OPS) |
| Visitor | Anyone | Reads the public site, signs in or up | React web (WEB-PUBLIC, AND-PUBLIC for app sign-in) |

## Core rules the UI expresses

- Login is OTP only (6 digits, 5 minutes, SMS / WhatsApp / email). No passwords.
- Milestones: pending → funded → claimed → verified → approved → released; verified → disputed → released or funded (rework).
- Evidence: pending_checks → accepted / rejected / flagged; flagged → accepted or rejected by ops. A flag never rejects a milestone by itself.
- Evidence is trusted only if it is (1) inside the site geofence, (2) device-signed, (3) not reused or edited, shown as the same three checks everywhere.
- No gallery upload anywhere; in-app camera only.
- A release needs BOTH supervisor verification and client approval; disputes pause release.
- AI drafts, checks and flags only, is always labelled and cites evidence; money figures come from the ledger.
- Money: client currency first (GBP, USD, EUR), then NGN and the FX rate. Times in the viewer's time zone.
- "Held by a licensed escrow partner, never by iBackHome." wherever money is shown or moved.

## Scope

| Priority | Meaning | In this package |
|---|---|---|
| P0 | Must ship for demo day | 59 screens |
| P1 | Ship if on schedule (designed in full) | 37 screens |
| P2 | Post-programme: "coming soon" placeholders only | 2 screens (FR-21 live walkthrough, FR-22 land and title verification) |

Out of scope for the programme (PRD): rent collection, caretaking and welfare visits, interior finishing supervision, iOS app, holding any client funds.

Demo-day MVP (PRD): project setup with BoQ, milestones and geofence; supervisor app with in-app capture, GPS and time stamps, geofence and offline sync; client dashboard with milestone approval and an AI weekly report; milestone escrow release (simulated if the partner isn't live); quote checker against the price index; perceptual hashing; supplier orders with on-site delivery confirmation.

Stack (Spec): FastAPI + PostgreSQL/PostGIS + Celery/Redis backend under `/api/v1`; React + TypeScript (Vite) web; Flutter Android; Stripe in, Paystack out, licensed escrow partner (simulated until signed).
