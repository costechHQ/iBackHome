# Missing endpoints

Things approved screens need that the Spec's API list does not provide. **Do not invent these endpoints in the backend from this list.** Build the screen against a mock adapter that returns the sample in that screen's `fixtures.json` → `mock_adapters`, log the gap (for example in the PR description and the acceptance checklist), and raise it with the backend owner.

| ID | Need | Detail | Screens that need it |
|---|---|---|---|
| MX-01 | Update own profile and preferences | Name, country, time zone, consent, notification channel order, quiet hours. The Spec has only GET /me. | WEB-CLIENT-001, WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-CONTRACTOR-009, WEB-SUPPLIER-006, WEB-CLIENT-023, WEB-OPS-013, AND-SUPERVISOR-015, WEB-SUPPLIER-008 |
| MX-02 | Project invitations | View, accept, decline, resend and cancel an invitation (contractor by client; supplier and ops user by ops). The Spec only says POST /projects "invites contractor". | WA-CONTRACTOR-001, WEB-CONTRACTOR-001, WEB-SUPPLIER-001, WEB-CLIENT-003, WEB-CLIENT-008, WEB-CONTRACTOR-003, WEB-OPS-008, WEB-OPS-012 |
| MX-03 | Payout recipient | Look up the account name, save, view and change the payout account for a contractor or supplier (payout_recipients table exists, no endpoint). | WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-SUPPLIER-001, WEB-CONTRACTOR-008, WEB-SUPPLIER-006, WEB-OPS-008 |
| MX-04 | Supplier business profile and verification | Create/update a supplier (name, address, location), ops verification steps and approve/suspend (suppliers table exists, no endpoint). | WEB-SUPPLIER-001, WEB-SUPPLIER-006, WEB-OPS-008 |
| MX-05 | Material order reads | List a project's orders, read one order, list a supplier's own orders, put payment on hold or cancel. The Spec has create, approve and delivery only. | WEB-CLIENT-019, WEB-CONTRACTOR-007, AND-CONTRACTOR-004, AND-SUPERVISOR-009, WEB-SUPPLIER-002, WEB-SUPPLIER-003, WEB-SUPPLIER-004 |
| MX-06 | Payout history | Contractor and supplier payouts list with references and advice PDFs (payouts table exists; GET /projects/{id}/ledger is client and ops only). | WEB-CONTRACTOR-003, WEB-CONTRACTOR-008, WEB-SUPPLIER-002, WEB-SUPPLIER-004, WEB-SUPPLIER-005 |
| MX-07 | Evidence detail and per-check results | Read one evidence item with the three check results (geofence, signature, reuse), its milestone and capture metadata. The gallery list returns status and reject_reason only. | WEB-CLIENT-011, WEB-CLIENT-013, WEB-OPS-005 |
| MX-08 | Send the BoQ back | The boq_review -> draft transition (client, contractor or ops, with a reason) has no endpoint. | WEB-CLIENT-005, WEB-CONTRACTOR-004, WEB-OPS-004 |
| MX-09 | Pause and resume a project | The ops-only active <-> paused transition has no endpoint. | WEB-OPS-004 |
| MX-10 | Dispute reads and two-approver steps | Read a dispute with its timeline, list a project's disputes, and record the first ops proposal before the second approval. The Spec has raise, resolve and the ops queue. | WEB-CLIENT-015, WEB-CONTRACTOR-006, WEB-OPS-006 |
| MX-11 | In-app notification feed | List the signed-in user's notifications and mark them read (notifications table exists, no endpoint). | WEB-CLIENT-008, WEB-CLIENT-020, AND-CONTRACTOR-005 |
| MX-12 | List my devices | GET the signed-in user's registered devices. The Spec has register and revoke only. | AND-SUPERVISOR-012, WEB-CONTRACTOR-010, AND-SUPERVISOR-015 |
| MX-13 | Report detail, edit and PDF | Read one report (body, evidence IDs, PDF link) and edit a draft before review. The Spec has list and review only. | WEB-CLIENT-018, AND-SUPERVISOR-011, WEB-OPS-010 |
| MX-14 | Spot-check history and sharing | Client and ops lists of completed spot checks, and ops "share with client" after closing. The Spec has the supervisor's list, schedule and complete only. | WEB-CLIENT-009, WEB-OPS-007 |
| MX-15 | Supervisor directory and vetting detail | List vetted supervisors with load and declared relations for assignment, and read one application for vetting. The Spec has assign, the vetting decision and the ops queue. | WEB-OPS-003, WEB-OPS-004, WEB-OPS-007 |
| MX-16 | Price index writes | Ops add/edit index entries and approve supplier price changes; supplier submits its own prices. The Spec has GET /price-index only. | WEB-SUPPLIER-007, WEB-OPS-009 |
| MX-17 | User administration | List users and change a user's status (suspend). The Spec has no user admin endpoints. | WEB-OPS-012 |
| MX-18 | Agent runs log | List agent_runs with tool calls for ops. No endpoint in the Spec. | WEB-OPS-011 |
| MX-19 | Sign out and sessions | Revoke the refresh token on sign-out and list or end active sessions. No endpoint in the Spec. | WEB-OPS-001, AND-SUPERVISOR-003, WEB-CLIENT-023 |
| MX-20 | Escrow balance per project | The "in escrow now" figure. escrow_accounts.balance_minor exists but no endpoint returns it; it may be derived from GET /projects/{id}/ledger. | WEB-CLIENT-007, WEB-CLIENT-009, WEB-CLIENT-013 |
| MX-21 | Ops money alerts and release retry | List failed releases and reconciliation mismatches, and retry a failed release. The Spec sends alerts by console and email but lists no endpoint. | WEB-OPS-002 |
| MX-22 | Receipts and exports | Release receipt PDF, ledger CSV export and audit log export. No endpoints in the Spec. | WEB-CLIENT-014, WEB-CLIENT-017, WEB-SUPPLIER-005, WEB-OPS-011 |
| MX-23 | Contractor public profile and track record | Contractor "About" text and computed track record. No endpoint in the Spec. | WEB-CONTRACTOR-009 |
| MX-24 | Supervisor visits for the client | Scheduled visits and the supervisor card (name, body, last visit) on the client dashboard. Partly in GET /projects/{id}; visit history has no endpoint. | WEB-CLIENT-009 |

## Missing fields on existing data

| Field | Where the designs use it | Note |
|---|---|---|
| Human-readable references (EV-2118, R-3307, P-0912, O-0141, D-0057, T-2291) | evidence, receipts, payouts, orders, disputes, ledger | The Spec uses UUIDs; only `payouts.reference` and `escrow_releases.provider_ref` exist. Fixtures carry them as `display_ref`. |
| Per-check evidence results | evidence detail, sync, ops review | Status + reject_reason only (MX-07). |
| Client-currency amount per milestone | all client money displays | Derived from ledger fx_rate; before funding it is an estimate at today's rate, and no endpoint returns today's rate. |
| Current FX rate for estimates | BoQ review, funding, contractor BoQ | Not in the Spec. |
| Order "on hold" | supplier order detail | Not a material_orders status. |
| Report reviewer name | reports, emails | Only via audit log. |
| User status "Deactivated" | ops users | users.status is active / suspended. |
| Supervisor rating and track record | ops vetting, contractor profile | supervisor_profiles.rating exists; contractor track record has no field (MX-23). |
| Checklist templates per milestone | supervisor checklist, milestone detail | Ops templates are assumed (Stage 1 G-10); no table or endpoint. |
