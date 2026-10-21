# Prototype flows (Stage 13)

Static, offline click-throughs of the five approved Stage 13 prototypes. Open any `.html` file in a browser: use the step list, Next/Back, or the screen's main button. Each step links to the full design of that screen.

## [A · Sign up to first funding](flow-a-sign-up-to-first-funding.html)

| Step | Title | Role | Screen |
|---|---|---|---|
| 1 | Landing | Visitor | [WEB-PUBLIC-001](../02-screens/stage-03-public-site/web-public-001-landing/spec.md) |
| 2 | Sign up: phone or email | Visitor | [WEB-PUBLIC-010](../02-screens/stage-04-auth-onboarding/web-public-010-sign-in/spec.md) |
| 3 | Enter the code | Visitor | [WEB-PUBLIC-010](../02-screens/stage-04-auth-onboarding/web-public-010-sign-in/spec.md) |
| 4 | Client onboarding | Client | [WEB-CLIENT-001](../02-screens/stage-04-auth-onboarding/web-client-001-client-onboarding/spec.md) |
| 5 | Create the project | Client | [WEB-CLIENT-003](../02-screens/stage-05-client-setup/web-client-003-projects-create/spec.md) |
| 6 | Site and boundary | Client | [WEB-CLIENT-004](../02-screens/stage-05-client-setup/web-client-004-site-geofence/spec.md) |
| 7 | Invite the contractor | Client | [WEB-CLIENT-003](../02-screens/stage-05-client-setup/web-client-003-projects-create/spec.md) |
| 8 | Review and approve the BoQ | Client | [WEB-CLIENT-005](../02-screens/stage-05-client-setup/web-client-005-boq-review/spec.md) |
| 9 | Fund Foundation | Client | [WEB-CLIENT-007](../02-screens/stage-05-client-setup/web-client-007-fund-first-milestone/spec.md) |
| 10 | Payment received, waiting for escrow | Client | [WEB-CLIENT-007](../02-screens/stage-05-client-setup/web-client-007-fund-first-milestone/spec.md) |
| 11 | Funded | Client | [WEB-CLIENT-007](../02-screens/stage-05-client-setup/web-client-007-fund-first-milestone/spec.md) |

## [B · Claim to release, every role](flow-b-claim-to-release.html)

| Step | Title | Role | Screen |
|---|---|---|---|
| 1 | Contractor claims Roofing | Contractor · app | [AND-CONTRACTOR-002](../02-screens/stage-08-contractor/and-contractor-002-projects-claim/spec.md) |
| 2 | Supervisor arrives on site | Supervisor · app | [AND-SUPERVISOR-005](../02-screens/stage-09-supervisor-android/and-supervisor-005-arrival-check/spec.md) |
| 3 | Capture with the in-app camera | Supervisor · app | [AND-SUPERVISOR-006](../02-screens/stage-09-supervisor-android/and-supervisor-006-capture/spec.md) |
| 4 | Review and notes | Supervisor · app | [AND-SUPERVISOR-006](../02-screens/stage-09-supervisor-android/and-supervisor-006-capture/spec.md) |
| 5 | Sync: all accepted | Supervisor · app | [AND-SUPERVISOR-007](../02-screens/stage-09-supervisor-android/and-supervisor-007-sync-queue/spec.md) |
| 6 | Verify Roofing | Supervisor · app | [AND-SUPERVISOR-008](../02-screens/stage-09-supervisor-android/and-supervisor-008-verify/spec.md) |
| 7 | Client: tap 1, the WhatsApp link | Client · phone | [WA-CLIENT-001](../02-screens/stage-12-cross-cutting/wa-client-001-whatsapp-messages/spec.md) |
| 8 | Client: tap 2, review | Client · phone | [WEB-CLIENT-014](../02-screens/stage-07-client-milestones-money/web-client-014-approve-release/spec.md) |
| 9 | Client: tap 3, confirm | Client · phone | [WEB-CLIENT-014](../02-screens/stage-07-client-milestones-money/web-client-014-approve-release/spec.md) |
| 10 | Releasing | Client · phone | [WEB-CLIENT-014](../02-screens/stage-07-client-milestones-money/web-client-014-approve-release/spec.md) |
| 11 | Released, with receipt | Client · phone | [WEB-CLIENT-014](../02-screens/stage-07-client-milestones-money/web-client-014-approve-release/spec.md) |
| 12 | Same milestone, four views · Client view | All roles | [WEB-CLIENT-013](../02-screens/stage-07-client-milestones-money/web-client-013-milestone-detail/spec.md) |
| 13 | Same milestone, four views · Contractor view | All roles | [WEB-CONTRACTOR-005](../02-screens/stage-08-contractor/web-contractor-005-milestones-claim/spec.md) |
| 14 | Same milestone, four views · Supervisor view | All roles | [AND-SUPERVISOR-008](../02-screens/stage-09-supervisor-android/and-supervisor-008-verify/spec.md) |
| 15 | Same milestone, four views · Ops view | All roles | [WEB-OPS-004](../02-screens/stage-11-ops-console/web-ops-004-projects/spec.md) |

## [C · Flagged evidence to ops decision](flow-c-flagged-evidence.html)

| Step | Title | Role | Screen |
|---|---|---|---|
| 1 | Supervisor saves EV-2243 | Supervisor · app | [AND-SUPERVISOR-006](../02-screens/stage-09-supervisor-android/and-supervisor-006-capture/spec.md) |
| 2 | Sync shows Flagged | Supervisor · app | [AND-SUPERVISOR-007](../02-screens/stage-09-supervisor-android/and-supervisor-007-sync-queue/spec.md) |
| 3 | Client sees “under review” | Client · web | [WEB-CLIENT-011](../02-screens/stage-06-client-dashboard-evidence/web-client-011-evidence-detail/spec.md) |
| 4 | Ops queue | Ops · console | [WEB-OPS-005](../02-screens/stage-11-ops-console/web-ops-005-flagged-evidence/spec.md) |
| 5 | Ops compares and decides | Ops · console | [WEB-OPS-005](../02-screens/stage-11-ops-console/web-ops-005-flagged-evidence/spec.md) |
| 6 | Result for everyone | All roles | [WEB-OPS-005](../02-screens/stage-11-ops-console/web-ops-005-flagged-evidence/spec.md) |

## [D · Dispute to ops resolution](flow-d-dispute-resolution.html)

| Step | Title | Role | Screen |
|---|---|---|---|
| 1 | Client sees Roofing verified | Client · web | [WEB-CLIENT-013](../02-screens/stage-07-client-milestones-money/web-client-013-milestone-detail/spec.md) |
| 2 | Raise a dispute | Client · web | [WEB-CLIENT-015](../02-screens/stage-07-client-milestones-money/web-client-015-dispute/spec.md) |
| 3 | Release paused | Client · web | [WEB-CLIENT-015](../02-screens/stage-07-client-milestones-money/web-client-015-dispute/spec.md) |
| 4 | Ops queue | Ops · console | [WEB-OPS-006](../02-screens/stage-11-ops-console/web-ops-006-disputes/spec.md) |
| 5 | Adaeze proposes release | Ops · console | [WEB-OPS-006](../02-screens/stage-11-ops-console/web-ops-006-disputes/spec.md) |
| 6 | Ngozi approves as second approver | Ops · console | [WEB-OPS-006](../02-screens/stage-11-ops-console/web-ops-006-disputes/spec.md) |
| 7 | Outcome for the client | Client · web | [WEB-CLIENT-015](../02-screens/stage-07-client-milestones-money/web-client-015-dispute/spec.md) |

## [E · Material order to supplier payout](flow-e-material-order-to-payout.html)

| Step | Title | Role | Screen |
|---|---|---|---|
| 1 | Contractor requests materials | Contractor · web | [WEB-CONTRACTOR-007](../02-screens/stage-08-contractor/web-contractor-007-material-requests/spec.md) |
| 2 | Client approves the order | Client · web | [WEB-CLIENT-019](../02-screens/stage-07-client-milestones-money/web-client-019-material-orders/spec.md) |
| 3 | Supplier gets WhatsApp | Supplier · phone | [WA-SUPPLIER-001](../02-screens/stage-10-supplier/wa-supplier-001-whatsapp-order/spec.md) |
| 4 | Supplier opens the order | Supplier · web | [WEB-SUPPLIER-004](../02-screens/stage-10-supplier/web-supplier-004-order-detail/spec.md) |
| 5 | Supervisor counts on site | Supervisor · app | [AND-SUPERVISOR-009](../02-screens/stage-09-supervisor-android/and-supervisor-009-confirm-delivery/spec.md) |
| 6 | Delivery confirmed | Supervisor · app | [AND-SUPERVISOR-009](../02-screens/stage-09-supervisor-android/and-supervisor-009-confirm-delivery/spec.md) |
| 7 | Supplier paid | Supplier · web | [WEB-SUPPLIER-005](../02-screens/stage-10-supplier/web-supplier-005-payouts/spec.md) |

The prototype boards share one state machine per flow on the canvas; here each step is a static snapshot of that state. Proto B's last step is expanded into the four role views (client, contractor, supervisor, ops).
