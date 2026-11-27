# ADR 0005: Supervisors apply through a public form; ops vet them; NIN is checked through a provider

- **Status:** Accepted for slice 1 (2026-11-27: the public form and its email to ops). Everything after slice 1 stays Proposed; open decisions are listed at the end.
- **Date:** 2026-11-11
- **Owner:** Christopher (decision), to be confirmed
- **Supersedes:** the supervisor sign-up path in `Docs/spec.md` where a new user signs up as `client` and applies in the app through `PUT /supervisors/me/profile`. That route stays for re-applying and editing.
- **Spec edits needed before any code:** a `supervisor_applications` table, the new routes below, the email templates, and the settings listed under "Settings".

## Context

Today the public page `/supervisors#apply` only links to `/contact`, which is a `mailto:` link. The vetting backend exists (`supervisor_profiles`, the four checks, the ops queue), but a profile needs an existing user with the `supervisor` role, and nothing in the code gives anyone that role except `scripts/seed.py`. A real applicant therefore cannot get into the flow.

We have decided that real supervisors apply through a form on the website, that ops (the `ops@ibackhome.com` mailbox) vet them, and that ops then reply with a link to download the app or with a rejection and reasons.

Three facts shape the design:

1. **We cannot check a NIN ourselves.** Only NIMC holds that data, and direct access needs accreditation. A NIN lookup goes through a licensed verification provider.
2. **COREN and NIOB checks stay manual.** COREN has an official portal page that checks a registration number (see the section on registration bodies). NIOB has no verification page we could find. Neither is known to offer an API.
3. **A NIN is very sensitive**, and the Nigeria Data Protection Act applies. A public form that anyone can post to is the wrong place to collect it.

## Decision

**1. A public application form with its own table.**

- The form on `/supervisors#apply` collects: full name, phone, email, state and city, registration body and number, years of experience, two guarantors (name and phone) and any relatives who are contractors (name and phone). It does not collect the NIN (see 3).
- `POST /supervisor-applications` is public (no login). It stores a `pending` application in a new `supervisor_applications` table, sends the applicant an acknowledgement email, and notifies ops. It accepts `Idempotency-Key`, is rate limited per IP, uses spam protection (a honeypot field; a CAPTCHA if needed), and returns the standard error shape. A second application from the same phone or email while one is `pending` or `approved` returns 409.
- The table is separate from `supervisor_profiles` because the applicant has no account yet. Phone is stored as E.164, the same way login does.

**2. Ops vet in the ops console and decide there.**

- The existing vetting queue and detail page are reused, reading from the new table. The four checks stay: registration, NIN, guarantor 1, guarantor 2.
- Approval needs all four checks ticked (same rule as today, 422 `vetting_checks_incomplete`). Rejection needs a written reason.
- Ops may leave a note on each check saying what they looked at (for example "COREN number R12345 active on the portal, 2026-11-12"). The decision and notes are audited. The audit log never contains the NIN.
- The decision routes are ops-only. Agents cannot approve or reject (architecture rule 4).

**3. NIN verification goes through a provider interface, after the form.**

- A `NinVerifier` interface in `base/` (the same pattern as `EscrowProvider`), with a `SimulatedNinVerifier` for local use and tests and one real implementation chosen later (see open decisions). The vetting logic does not depend on which provider is used.
- The NIN is not collected on the public form. It is collected once the applicant has been shortlisted, either by ops asking for it on the review screen or by the applicant in the app. It is stored encrypted with `NIN_ENCRYPTION_KEY` and wiped when ops decide, as today (only the last four digits remain).
- A check runs once per applicant, on ops' request, never on form submission, so spam applications cost nothing. The result (matched or not, the provider's reference, the time) is stored; the raw response is not kept. A provider outage returns a clear error and ops can fall back to a manual check.
- A match fills the "NIN matched" check as a suggestion. Ops still make the final decision.
- A plain lookup proves the NIN exists and belongs to the stated name and date of birth. It does not prove the applicant is that person; only a selfie face match does. Whether to require the face match is an open decision.

**4. Registration bodies are checked manually.**

- Ops check the registration number on the body's own register and record the result in the check note. No provider is integrated for COREN or NIOB at this stage.
- The form's registration body is a fixed list (COREN, NIOB, CORBON, other) with the number, so ops know which register to use.

**5. Approval creates the account and sends the email.**

- On approval, in one transaction: create (or find) the user by phone, set role `supervisor` (a number that already belongs to another role gets 409 `role_conflict`, and the role is never changed by an approval), create the `supervisor_profiles` row already `approved`, and write the audit entries.
- After the commit, an email from `ops@ibackhome.com` gives the app download link and says to sign in with the phone number. Reasons and the link are queued after commit, like other notifications.
- On rejection, an email gives the reasons and says the applicant may apply again. The applicant can re-apply once the issue is fixed.
- Closing this path fixes the gap where nothing grants the `supervisor` role.

## Slice 1: what is built first (accepted 2026-11-27)

The form on `/supervisors#apply`, saved in `supervisor_applications` and emailed to ops. Nothing else from this ADR ships in this slice.

- **Form fields:** full name, phone, email, state and city, registration body (COREN, NIOB, CORBON, other) and registration number, years of experience, two guarantors (name and phone), declared relatives who are contractors (optional), consent. No NIN.
- **Registration first, identity second.** The NIN check costs money per lookup, so ops review in this order: (1) check the registration number on the body's own register, (2) call both guarantors, (3) only then ask for the NIN and run the paid check. The email to ops states this order.
- **Sent to ops@ibackhome.com** (setting `OPS_NOTIFY_EMAIL`) after the application is saved, with a receipt to the applicant. The application is stored first, so a failed email never loses it.
- **Spam:** a hidden honeypot field, a per-IP rate limit and a 409 for a second pending application with the same phone or email. CAPTCHA is deferred (open decision 6).
- **Retention:** rejected applications are kept 12 months, then deleted (proposed for open decision 5; confirm with legal advice).
- **Not in slice 1:** the ops queue and decision routes that create the account, the NIN provider, the app-link email. Until the decision route exists, ops promote an approved applicant by hand.

## Settings (all optional until used; none contain real values in the repo)

`OPS_FROM_EMAIL`, `OPS_REPLY_TO`, `APP_DOWNLOAD_URL`, the existing `EMAIL_SMTP_*` settings, `NIN_ENCRYPTION_KEY`, and the chosen provider's keys (`NIN_PROVIDER`, plus its own variables).

## Consequences

- A new table, a migration after the current head, three public or ops routes plus the verifier interface, email templates and a web form. All need tests (permissions, rate limit, duplicate 409, role conflict, the transaction, no NIN in the audit log).
- A third party receives NINs. That needs a data-processing agreement with the provider, a privacy-policy change and legal advice on the Nigeria Data Protection Act before the first real check.
- The public endpoint is the first unauthenticated write apart from OTP, so it needs abuse protection from day one.
- Ops carry the manual registration and guarantor checks. This is slow but accurate, and the notes make it auditable.
- Email must be configured (SMTP host, a sending domain with SPF and DKIM, the mailbox) before this can ship; otherwise acknowledgements and decisions are not delivered.
- If a supervisor can also be a contractor (under discussion in a separate ADR), approval must not block that later.

## Alternatives considered

- **Keep sign-up in the app only.** Needs a published app and still has no way to grant the role. Rejected.
- **Collect the NIN on the public form.** Simpler for ops, but puts the most sensitive field on an open form. Rejected.
- **Verify the NIN on every submission.** Pays for spam. Rejected.
- **Integrate with NIMC directly.** Needs accreditation; not realistic for this team now. Rejected.
- **Email-only applications (the current `mailto:`).** No structure, no audit trail, no queue. Rejected.

## Open decisions

1. **NIN provider and whether to require a selfie match.** Candidates are Dojah, Smile ID and Youverify; prices and NIMC accreditation must be confirmed in writing.
2. **How the app link is delivered.** An APK link, Firebase App Distribution or a Play Store internal test link. The app is not published yet.
3. **When the NIN is collected** (ops request on the review screen, or the app after approval).
4. **Mailbox and sending domain** for `ops@ibackhome.com`, and where replies go.
5. **Data protection:** the retention period for rejected applications, and a legal review of the provider agreement.
6. **Spam protection:** honeypot only, or a CAPTCHA provider.
