# ADR 0007: Contractor matching: contractors apply, ops vet them, ops shortlist, the client chooses

- **Status:** Accepted (2026-11-27, product owner). Built: phase 1 (applications, vetting, directory; PRs #146 and #147) and phase 2 (match requests; PRs #148 and #149). Phase 3 is the public wording and the assistant answers.
- **Date:** 2026-11-27
- **Owner:** Christopher (decision)
- **Spec edits:** four tables, the routes, and the match-request state machine (in this PR).

## Context

Today a client must bring their own contractor: `POST /projects` takes an optional `contractor_phone` and the
contractor is invited by phone. There is no way to say "find me a contractor", no directory of contractors, and no way
to set a contractor on a project after it is created (`projects/service.py` has `create_project` and no setter). The PRD
has no matching requirement (it says the contractor is "hired by the client"); an earlier plan noted that matching had
been claimed but did not exist.

The product owner chose, on 2026-11-27: **an ops-assisted shortlist** (not a browsable marketplace, not automatic
ranking), **contractors only** (not engineers or architects), and **contractors apply and ops vet them**.

## Decision

**1. Contractors apply, ops vet them.**

- A public form on `/contractors` (no login) saves a `contractor_applications` row and emails ops. Same protections as
  the supervisor form (ADR 0005, slice 1): honeypot, per-IP limit, `Idempotency-Key`, a 409 for a second pending
  application with the same phone or email, no sensitive ID collected, emails queued after commit so an email outage
  never loses an application.
- **Fields:** business name, contact name, phone, email, states served (one or more), specialties (a fixed list:
  buildings, roofing, finishing, civil works, other), years in business, number of projects completed (a declared
  figure), registration details where they have them (CAC RC number, CORBON number), two references (name and phone),
  a consent tick (the applicant agrees to be contacted, to their references being called, and to appearing in client
  shortlists). **No NIN** on the public form.
- Ops vet in the ops console, like supervisor vetting: tick the checks (registration where applicable, reference 1,
  reference 2; identity later), write notes, approve or reject with a written reason. Approval needs the required checks
  ticked (422 `vetting_checks_incomplete`).
- **Approval** creates or finds the contractor's user by phone and writes the `contractor_profiles` row, in one
  transaction. A number that already belongs to a client, supervisor, supplier or ops user is 409 `role_conflict` and its
  role is never changed (the same rule as `users.invite_contractor`). After the commit the contractor is emailed.
- The text on a profile is written by ops from the application, so nothing unreviewed is shown to clients.

**2. A client asks for a match; ops shortlist; the client chooses.**

- Only the owner of a **draft project that has no contractor** can ask: "Find me a contractor", with a brief (state and
  city, budget, type of work, timeline, notes). One open request per project (409 `match_request_exists`). Ops are
  emailed.
- Ops pick **1 to 3** approved, listed, active contractors from the directory (filter by state and specialty) after
  phoning each to confirm they are free and interested (offline). The client is notified.
- The client sees, for each shortlisted contractor: business name, states served, specialties, years in business,
  projects completed (declared, plus projects on iBackHome), and "vetted by iBackHome". **Never a phone number or
  email**, so nobody goes around us.
- The client **chooses one**. That invites the contractor exactly as project creation does
  (`users.invite_contractor`), sets the project's contractor through a new `projects.set_contractor()`, notifies the
  contractor and audits it. The existing flow continues: BoQ, approvals, funding.

**3. State machine** (in `Docs/spec.md`): `open` to `shortlisted` (ops), `shortlisted` to `matched` (client),
`open` or `shortlisted` to `cancelled` (client or ops), `shortlisted` to `open` (ops, to replace the list). Every change is
checked in the feature's `service.py`, audited, and an invalid move is 409.

**4. `projects.set_contractor(session, project_id, contractor_id, actor_id)`.** The first way to attach a contractor
after creation. Draft projects only (409 `project_not_draft`), audited, called only through `projects/service.py`.

**5. Money is untouched.** No fee, no payment and no escrow step in matching.

## Consequences

- A new feature folder `backend/app/features/contractors/` (owner Christopher; James and Gabriel as reviewers), a
  migration for four tables (`contractor_applications`, `contractor_profiles`, `match_requests`, `match_shortlist`), new
  ops screens, a client screen on draft projects, and the public form.
- The ops team now carries vetting and shortlisting work (calls to contractors and references). It is manual by design
  for the pilot.
- Contractor details are shown to clients who request a match: the privacy policy needs one line saying so.
- If this works, a browsable directory or automatic ranking can follow; the tables do not rule that out.
- Contractors who already work with a client are unaffected: inviting by phone stays.

## Alternatives considered

- **A browsable directory.** More self-service but needs enough contractors to look credible and more screens.
  Possible later.
- **Automatic matching.** Needs real data (profiles, completed projects) first; not realistic for the pilot.
- **Matching engineers and architects too.** Needs a new role or profile type and rules for how they fit a project.
  Not now.
- **Ops add contractors by hand, no public form.** Simplest but slow to grow and no audit of what the applicant said.

## Open decisions

1. The exact vetting checks for contractors (proposal above) and which registrations apply to a builder (CAC, CORBON).
2. Whether and how contractors are told about a shortlist before the client chooses (the process says ops phone them).
3. The privacy-policy sentence about profile details shown to clients.
4. Whether matching stays free (nothing is charged in this design).
