# iBackHome — Product Requirements Document

Oct 7, 2026 · @Lilian Ezichi Ezeh

## Summary

iBackHome (said "eyes back home") lets Nigerians abroad build homes in Enugu with confidence: verified supervisors capture evidence that can't be faked, and money is released milestone by milestone through a licensed escrow partner only when the work is confirmed. We are not a construction company. The client keeps their own contractor; iBackHome verifies what the contractor claims and controls when money moves.

**Tagline:** Far from home, never out of sight.

**Supporting line:** Proof, not promises.

| Item | Detail |
| --- | --- |
| Programme | HackathonAfrica 3.0, Team 4 |
| Build window | 20 working days, 4 gates, ending in demo day |
| Platforms | React web (client, contractor, ops), Flutter Android (supervisor, contractor) |
| Agentic AI | Report agent, image checks, quote checker, WhatsApp assistant |
| Document status | Draft v0.1, to be revised after week-1 interviews |

The feature list below is a starting hypothesis. We change it based on what we learn from at least 20 interviews in week one.

## Problem, goals and success metrics

People abroad lose years of savings building houses at home because they cannot verify what happens on site. The usual causes are diverted materials, inflated quotes, old or borrowed progress photos, and money spent elsewhere. The damage is financial and personal: family relationships break down.

**Why it sells**

- The buyer already feels the pain and already spends large sums on the project.
- They pay in foreign currency, so our fee is small next to the project value.
- No new habit: they already send money and ask for photos. We make the photos trustworthy.
- Customers are cheap to reach through diaspora WhatsApp and Facebook groups, hometown unions and churches abroad.

**Goals for demo day**

1. Prove that site evidence captured through iBackHome cannot be faked or reused.
2. Prove that money moves only after a supervisor verifies and the client approves a milestone.
3. Show at least one real Enugu site tracked live for a real client abroad.
4. Show unit economics built from field data, not assumptions.

| Metric | Target by demo day | How we measure |
| --- | --- | --- |
| Discovery interviews | 20+ (15+ diaspora builders, 5+ contractors/builders) | Interview log |
| Pilot projects tracked | 2 to 5 real sites | Projects in production |
| Evidence items captured in-app | 100+ across pilot sites | Evidence table |
| Evidence rejected (outside geofence or reused) | Logged and reported | Rejection log |
| Milestone approval and escrow release | At least 1 end to end (simulated if partner not live) | Audit log |
| Weekly AI reports delivered | 1 per pilot project per week | Report table |
| Client willingness to pay | Price point tested with 10+ prospects | Interview notes |

## Users and roles

Five roles share one platform; the client abroad is the payer and the primary user.

| Role | Who they are | What they do in the system | Main surface |
| --- | --- | --- | --- |
| Client abroad | Nigerian in the UK, US, Canada, Europe building in Enugu | Sets up the project, funds milestones, approves releases, reads reports, books live walkthroughs | Web dashboard, WhatsApp |
| Contractor | Builder hired by the client | Submits the bill of quantities, claims milestones, requests materials | Web portal, Android |
| Supervisor | Registered builder or engineer vetted by iBackHome | Visits on schedule and for spot checks, captures evidence, verifies milestones | Android app (offline-first) |
| Supplier | Verified seller of cement, blocks, rods and other materials | Receives material orders, delivers to site, gets paid directly | Web portal, WhatsApp |
| Operations | iBackHome staff | Vets supervisors and suppliers, schedules spot checks, assigns rotations, resolves disputes | React admin console |

**Personas to validate in interviews**

- **Chioma, 38, nurse in Manchester.** Sends about £1,500 a month to her brother for a 4-bedroom bungalow in Independence Layout. Photos arrive late and look similar each week. Wants proof, not reassurance.
- **Emeka, 45, engineer in Houston.** Lost money on a first project. Will pay well for control but has no time; wants a weekly summary and the ability to approve payments from his phone.
- **Engr. Obi, contractor in Enugu.** Honest and good at his job but paid late because clients don't trust him. Sees iBackHome as faster payment and a public track record.

## Scope

Demo day ships the evidence-and-escrow core; anything that doesn't prove trust or move money waits.

**In scope (demo-day MVP)**

- Project setup with bill of quantities, milestones and a site geofence
- Supervisor app with in-app-only capture, GPS and time stamps, geofence enforcement and offline sync
- Client dashboard with milestone approval and an AI-generated weekly report
- Milestone escrow release (simulated if the escrow partner isn't live)
- Quote checker flagging an inflated line against the materials price index
- Perceptual hashing to catch reused images
- Supplier orders with on-site delivery confirmation
- At least one real Enugu site tracked live

**Cut first if behind (in this order)**

1. WhatsApp assistant
2. Live video walkthroughs
3. Land and title verification

**Out of scope for the programme**

- Rent collection, caretaking and welfare visits (growth path after a house is finished)
- Interior finishing supervision add-on
- iOS app
- Holding any client funds ourselves: all money sits with a licensed escrow partner

**Assumptions to test in week one**

- Clients will pay a monthly fee in foreign currency on top of the escrow fee.
- Contractors will accept supervision if it means faster payment.
- Registered builders in Enugu will take supervisor work at a per-visit rate we can afford.
- An escrow partner can onboard us, or will let us simulate their flow for the demo.

## Functional requirements

P0 = must ship for demo day, P1 = ship if on schedule, P2 = post-programme.

| ID | Module | Requirement | Acceptance criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-01 | Accounts | Phone or email login with OTP; roles for client, contractor, supervisor, supplier, ops | Each role sees only its own screens; login works on web and Android | P0 |
| FR-02 | Accounts | Supervisor vetting: professional registration check, NIN, two guarantors | Supervisor cannot be assigned until ops marks all checks passed | P0 |
| FR-03 | Project setup | Create project with client, contractor, supervisor, address | Project visible to all three parties with correct permissions | P0 |
| FR-04 | Project setup | Pin site on map and draw a geofence polygon | Polygon saved in PostGIS; shown on client and ops maps | P0 |
| FR-05 | Project setup | Bill of quantities with line items grouped into milestones (foundation, blockwork to lintel, roofing, plastering, finishing) | Client, contractor and ops all approve the BoQ before funding opens | P0 |
| FR-06 | Evidence | Photo and video capture only through the in-app camera; gallery upload blocked | No code path accepts a file from device storage | P0 |
| FR-07 | Evidence | Every capture GPS- and time-stamped, with metadata signed on device | Server rejects captures with missing or tampered signatures | P0 |
| FR-08 | Evidence | Server accepts evidence only from inside the site geofence | Capture 50 m outside the polygon is rejected and logged | P0 |
| FR-09 | Evidence | Offline capture with later sync, keeping original capture time and location | Captures taken with no signal upload correctly when online | P0 |
| FR-10 | Evidence | Perceptual hash of every image; flag near-duplicates across all projects | Re-submitting an old photo from another site is flagged | P0 |
| FR-11 | Supervision | Scheduled visits plus unannounced spot checks; supervisor rotation | Ops can schedule a spot check without notifying the contractor | P1 |
| FR-12 | Milestones | Contractor claims a milestone; supervisor verifies with evidence checklist | Milestone moves Claimed → Verified only with required evidence attached | P0 |
| FR-13 | Escrow | Client funds milestones by Stripe; funds held by licensed escrow partner | Funding shows in ledger; iBackHome never holds funds | P0 |
| FR-14 | Escrow | Release only after supervisor verification and client approval; disputes pause release | Release blocked without both approvals; every step audit-logged | P0 |
| FR-15 | Client dashboard | Progress vs plan, spend vs budget, evidence gallery, milestone approvals | Client can approve a milestone in under 3 taps on mobile web | P0 |
| FR-16 | Suppliers | Order materials from verified suppliers; on-site delivery confirmed with photos and quantities | Supplier paid directly by Paystack only after delivery confirmed | P1 |
| FR-17 | Price index | Current Enugu prices for key materials from partner suppliers | Index has 15+ items with date of last update | P0 |
| FR-18 | Reports | Weekly report per project (see AI layer) | Report generated and sent every week of the pilot | P0 |
| FR-19 | Ops console | Vetting queue, spot-check scheduler, dispute queue, live map of sites | Ops can resolve a dispute and log the decision | P0 |
| FR-20 | Notifications | WhatsApp, email and push for claims, approvals, reports and flags | Client gets a message within 5 minutes of a milestone claim | P1 |
| FR-21 | Live walkthrough | Book a video walkthrough in the client's time zone via third-party video SDK | Client joins a call with the supervisor on site | P2 |
| FR-22 | Add-ons | Land and title verification before purchase | Request form and ops workflow | P2 |
| FR-23 | Audit | Every money movement and sensitive action logged: who, what, when, where | Audit log viewable in ops console; cannot be edited | P0 |

## AI layer

The AI drafts, checks, flags and answers; a human approves anything that moves money. Agents call the iBackHome REST API through tool calling and never read the database directly.

| Component | What it does | Inputs | Output | Guardrails | Priority |
| --- | --- | --- | --- | --- | --- |
| Report agent | Turns the week's photos, supervisor notes and spending into a clear report against the BoQ | Evidence, verifications, ledger, BoQ | Weekly report (web + PDF + WhatsApp summary) | Only states facts from project data; cites the evidence it used; supervisor reviews before send in pilot | P0 |
| Image checks | Detects reused or edited photos, checks metadata, estimates building stage to cross-check the claimed milestone | Image, perceptual hash index, signed metadata | Flag with reason and confidence | Flags go to ops; a flag never rejects a milestone by itself | P0 (reuse), P1 (stage estimate) |
| Quote checker | Reads a contractor quote and flags lines priced above the index or quantities that don't fit the plan | Quote PDF or BoQ, price index, house plan size | Flagged lines with index price and % difference | Advisory only; client and ops decide | P0 |
| WhatsApp assistant | Answers questions like "how far is my roofing?" or "what's left in my budget?" | Client's question, project API | Short answer with link to dashboard | Read-only tools; cannot approve or release anything; hands off to ops on disputes | P1 |

**Hard rules**

- No agent has a tool that releases escrow, approves a milestone or pays a supplier.
- Every agent conversation and tool call is logged.
- Answers about money always come from the ledger, never from the model's own estimate.
- The demo uses real pilot data for at least one component (programme requirement).

## Key user flows

The milestone release flow is the heart of the product: every other flow feeds evidence or money into it.

&#91;embedded content: milestone release flow · 2 checks, 1 dispute path\]

Checks = inside the geofence, valid device signature, no reused or edited image. A failed check or a client dispute pauses the release and goes to ops, who can ask for new evidence.

1. **Project setup.** Client invites contractor → contractor submits BoQ → ops assigns a vetted supervisor → site pinned and geofence drawn → all parties approve BoQ → client funds the first milestone through Stripe into escrow.
2. **Site visit.** Supervisor opens the project in the app → app confirms they are inside the geofence → captures photos and video through the in-app camera → adds notes → evidence syncs (immediately or when signal returns).
3. **Milestone release.** As drawn above.
4. **Material order.** Contractor requests materials → quote checked against price index → client approves order → supplier delivers → supervisor confirms quantities with photos on site → supplier paid directly by Paystack.
5. **Weekly report.** Every Friday the report agent drafts the report → supervisor reviews in pilot → client receives it on the dashboard and as a WhatsApp summary.
6. **Spot check.** Ops schedules an unannounced visit by a rotated supervisor → evidence compared with the contractor's latest claims → mismatches flagged.

## Non-functional requirements

| Area | Requirement |
| --- | --- |
| Evidence integrity | Metadata signed on device with a per-install key; server verifies signature, geofence and timestamp drift (reject if device time is off by more than 10 minutes from GPS/network time) |
| Security | Role-based access on every endpoint; OTP login; secrets in environment, never in the repo |
| Money safety | Idempotent webhook handling for Stripe and Paystack; double-entry ledger; automated tests on every money-moving path |
| Audit | Append-only audit log of every write that matters, with actor, time and IP/device |
| Data protection | Comply with the Nigeria Data Protection Act: consent at sign-up, minimal collection, privacy policy before pilot |
| Offline | Supervisor app captures and queues evidence with no signal; syncs when back online |
| Low-end devices | Supervisor app runs on Android 8+ with 2 GB RAM; images compressed before upload |
| Performance | Client dashboard loads in under 3 seconds on 4G; evidence upload under 30 seconds per photo on 3G |
| Time zones | All times stored in UTC; shown in the client's local time zone |
| Currency | Client pays in USD, GBP or EUR; supplier and contractor payouts in NGN; exchange rate recorded per transaction |
| Availability | Staging from week two; production deploy by day 15; daily merge-and-deploy at 17:00 |

## Architecture and data model

We build our own base (auth, roles, audit log, payments wrapper, notifications, geo utilities, agent toolkit, admin shell). On top of it we add iBackHome's own services.

&#91;embedded content: system architecture · main components\]

Agents never touch the database directly; they use the same API and permissions as any other client.

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | FastAPI | Shared starter; one service per domain |
| Database | PostgreSQL + PostGIS | Site geofences, point-in-polygon checks, supervisor routing |
| Jobs | Celery + Redis | Weekly reports, reminders, hash indexing |
| Web | React | Client dashboard, contractor/supplier portals, ops console |
| Mobile | Flutter | Supervisor app on low-end Android, offline-first |
| Payments | Stripe (client abroad), Paystack (local payouts), licensed escrow partner | We never hold client funds |
| Image integrity | Perceptual hashing (pHash), EXIF and signed metadata | Detect reuse across all projects |
| Video | Third-party SDK | Live walkthroughs (P2) |
| AI | LLM API with tool calling | Report agent, quote checker, assistant |
| Infra | Docker, GitHub Actions CI | Staging from week two |

**Core data model**

- Client, Contractor, Supervisor, Supplier (users with roles)
- Project → Site → Geofence
- Project → BoQItem → Milestone
- Milestone → Evidence (photo/video, GPS, timestamp, signature, pHash) → Verification → Approval → EscrowRelease
- Supplier → MaterialOrder → Delivery; PriceIndexEntry
- Report, SpotCheck, Dispute, AuditLog, LedgerEntry

## Business model and unit economics

Revenue comes from four streams; every price below is a placeholder until week-one interviews give us real numbers.

| Revenue stream | How it works | Figure to collect in week one |
| --- | --- | --- |
| Supervision subscription | Monthly fee per project in USD, GBP or EUR | What clients would pay per month; what they lose today |
| Escrow release fee | Small percentage of each milestone released | Escrow partner's own fee; typical milestone size |
| Materials margin | Margin or referral fee on materials bought through partner suppliers | Supplier willingness to pay a referral fee |
| Add-ons | Land verification, extra walkthroughs, finishing supervision | Price clients would accept per add-on |

**Cost per project per month to model**

- Supervisor visits (scheduled + spot checks) × rate per visit, plus transport
- Escrow partner fees and payment processing (Stripe, Paystack)
- Storage for photos and video, LLM API calls for reports and checks
- Ops time for vetting and disputes

**Unit economics we will present**: contribution margin per project per month = subscription + release fees + materials margin − supervisor cost − payment and escrow fees − infrastructure and AI cost.

**Growth path**: once a house is finished, the same supervisors manage it — rent collection, repairs, caretaking and welfare visits to elderly parents (a natural link to NdụCare).

## Delivery plan

Four gates decide the pace: problem validated (day 5), core flows on staging (day 12), pilot data in (day 18), demo day (day 20). Missing a gate means a mentor review and reduced scope, so anything needing an outside party starts in week one.

| Phase | Days | Product work | Outside work | Gate |
| --- | --- | --- | --- | --- |
| Discovery | 1–3 | Spike in-app capture with signed metadata; fork the shared starter repo | 20+ interviews, materials price survey, pilot clients recruited, escrow partner talks, supervisor recruitment | — |
| Setup | 4–5 | Data model, auth and roles, project/BoQ/milestone APIs, app and web shells, CI and staging, seed data, price index v1 | Follow up interviews; confirm pilot sites | Problem validated (day 5) |
| Core build | 6–12 | Evidence API with geofence check, capture app with offline sync, milestone state machine, Stripe funding, simulated escrow release, client dashboard, ops console, perceptual hashing, quote checker v1, supplier orders | Supervisor vetting; supplier onboarding | Core flows end to end on staging (day 12) |
| AI layer | 13–15 | Report agent, image stage check, WhatsApp assistant if on time, notifications, production deploy | Load real pilot projects | — |
| Pilot | 16–18 | Fix issues found on site; weekly reports on real data | Track 2–5 real sites with real clients abroad; collect metrics | Pilot data in (day 18) |
| Pitch | 19–20 | Architecture doc, ADRs, demo build | Unit economics, risk register, rehearsal | Demo day (day 20) |

**Gate checklist**

- [ ] Day 5: 20+ interviews logged, price survey done, pilot clients named, escrow partner contacted
- [ ] Day 12: project → evidence → claim → verify → approve → release works end to end on staging
- [ ] Day 18: real sites tracked, real reports sent, metrics collected
- [ ] Day 20: all demo-day deliverables complete

## Risks, open questions and demo-day checklist

| Risk | Mitigation |
| --- | --- |
| Supervisor colludes with contractor | Rotation, random spot checks, client can join live video, ratings, guarantors |
| Escrow regulation | Licensed escrow partner; iBackHome never holds client funds; simulate for demo if needed |
| Clients abroad don't trust a new platform | Registered professionals, transparent process, early testimonials, insurance where possible |
| Contractors refuse supervision | Position as protection for good contractors: faster payment and a public track record |
| Evidence spoofing (fake GPS, old photos) | In-app capture only, geofence, signed metadata, perceptual hashing, time-drift check |
| No real pilot site ready by day 16 | Recruit from cohort members' own relatives abroad in week one; line up 5 to land 2 |
| AI report states something untrue | Reports built only from project data, cite evidence, supervisor review before send |
| Data protection breach | Consent, minimal data, privacy policy before pilot, access logging |

**Open questions**

- Which licensed escrow partner, and how long does onboarding take?
- What monthly price do clients accept, and in which currency first (GBP or USD)?
- What do registered builders in Enugu charge per site visit?
- Which professional body do we verify supervisors against (COREN, NIOB or both)?
- Exact calendar dates for days 1 to 20 and demo day.

**Demo-day deliverables**

- [ ] Working web app and Android build, deployed to production
- [ ] At least one agentic AI component running on real data
- [ ] Live pilot results: users, transactions, retention and what we learned
- [ ] Unit economics built from field data
- [ ] Architecture document and ADRs
- [ ] Repository with tests, README and setup instructions
- [ ] 10-minute pitch and 5-minute live demo
- [ ] Risk register with legal and regulatory items
