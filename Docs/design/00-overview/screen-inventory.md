# Screen inventory

Final list of the 98 approved screens in this package (Stages 3–12). Each row links to its spec; `screen.html`, screenshots and `fixtures.json` sit in the same folder. Machine-readable copy: [manifest.json](../manifest.json).

ID format: `<SURFACE>-<ROLE>-<NNN>`. SURFACE is `WEB` (desktop and mobile web), `AND` (Flutter Android), `WA` (WhatsApp template) or `EMAIL`. A WEB screen with only 390px frames has surface `mobile-web`.

| ID | Title | Surface | Role | Stage | Priority | FR IDs | States | Spec |
|---|---|---|---|---|---|---|---|---|
| WEB-PUBLIC-001 | Landing page | web | public | 3 | P1 | — | 2 | [spec](../02-screens/stage-03-public-site/web-public-001-landing/spec.md) |
| WEB-PUBLIC-002 | How it works | web | public | 3 | P1 | FR-08, FR-10, FR-14 | 2 | [spec](../02-screens/stage-03-public-site/web-public-002-how-it-works/spec.md) |
| WEB-PUBLIC-003 | Pricing | web | public | 3 | P1 | FR-21, FR-22 | 2 | [spec](../02-screens/stage-03-public-site/web-public-003-pricing/spec.md) |
| WEB-PUBLIC-004 | For contractors | web | public | 3 | P1 | — | 2 | [spec](../02-screens/stage-03-public-site/web-public-004-for-contractors/spec.md) |
| WEB-PUBLIC-005 | Become a supervisor | web | public | 3 | P1 | FR-02 | 2 | [spec](../02-screens/stage-03-public-site/web-public-005-become-a-supervisor/spec.md) |
| WEB-PUBLIC-006 | Trust and safety | web | public | 3 | P1 | FR-07, FR-08, FR-10, FR-14, FR-23 | 2 | [spec](../02-screens/stage-03-public-site/web-public-006-trust-and-safety/spec.md) |
| WEB-PUBLIC-007 | Contact | web | public | 3 | P1 | — | 2 | [spec](../02-screens/stage-03-public-site/web-public-007-contact/spec.md) |
| WEB-PUBLIC-008 | Privacy policy | web | public | 3 | P0 | — | 2 | [spec](../02-screens/stage-03-public-site/web-public-008-privacy-policy/spec.md) |
| WEB-PUBLIC-009 | Terms | web | public | 3 | P0 | — | 2 | [spec](../02-screens/stage-03-public-site/web-public-009-terms/spec.md) |
| WEB-PUBLIC-010 | Sign in or sign up | web | public | 4 | P0 | FR-01 | 13 | [spec](../02-screens/stage-04-auth-onboarding/web-public-010-sign-in/spec.md) |
| AND-PUBLIC-001 | Sign in (Android) | android | public | 4 | P0 | FR-01 | 2 | [spec](../02-screens/stage-04-auth-onboarding/and-public-001-sign-in/spec.md) |
| WA-CONTRACTOR-001 | Invitation message (WhatsApp) | whatsapp | contractor | 4 | P0 | FR-03 | 1 | [spec](../02-screens/stage-04-auth-onboarding/wa-contractor-001-invitation-message/spec.md) |
| WEB-CONTRACTOR-001 | Accept an invitation | web | contractor | 4 | P0 | FR-03, FR-01 | 7 | [spec](../02-screens/stage-04-auth-onboarding/web-contractor-001-accept-invitation/spec.md) |
| WEB-CLIENT-001 | Client onboarding | web | client | 4 | P0 | FR-01 | 6 | [spec](../02-screens/stage-04-auth-onboarding/web-client-001-client-onboarding/spec.md) |
| WEB-CONTRACTOR-002 | Contractor onboarding | web | contractor | 4 | P0 | FR-01, FR-03 | 4 | [spec](../02-screens/stage-04-auth-onboarding/web-contractor-002-contractor-onboarding/spec.md) |
| AND-CONTRACTOR-001 | Contractor onboarding (Android) | android | contractor | 4 | P0 | FR-01, FR-03 | 3 | [spec](../02-screens/stage-04-auth-onboarding/and-contractor-001-contractor-onboarding/spec.md) |
| WEB-SUPPLIER-001 | Supplier onboarding | web | supplier | 4 | P1 | FR-16, FR-01 | 4 | [spec](../02-screens/stage-04-auth-onboarding/web-supplier-001-supplier-onboarding/spec.md) |
| AND-SUPERVISOR-001 | Supervisor application and vetting status | android | supervisor | 4 | P0 | FR-02 | 9 | [spec](../02-screens/stage-04-auth-onboarding/and-supervisor-001-supervisor-application/spec.md) |
| AND-SUPERVISOR-002 | Permissions and capture key | android | supervisor | 4 | P0 | FR-06, FR-07 | 3 | [spec](../02-screens/stage-04-auth-onboarding/and-supervisor-002-permissions-device-key/spec.md) |
| WEB-OPS-001 | Ops sign-in and session | web | ops | 4 | P0 | FR-01, FR-19 | 4 | [spec](../02-screens/stage-04-auth-onboarding/web-ops-001-ops-sign-in/spec.md) |
| WEB-CLIENT-002 | Session expired (mobile web) | mobile-web | client | 4 | P0 | FR-01 | 1 | [spec](../02-screens/stage-04-auth-onboarding/web-client-002-session-expired-mobile/spec.md) |
| AND-SUPERVISOR-003 | Session expired and sign out (Android) | android | supervisor | 4 | P0 | FR-01, FR-09 | 2 | [spec](../02-screens/stage-04-auth-onboarding/and-supervisor-003-session-sign-out/spec.md) |
| WEB-CLIENT-003 | Projects and create project | web | client | 5 | P0 | FR-03, FR-05 | 7 | [spec](../02-screens/stage-05-client-setup/web-client-003-projects-create/spec.md) |
| WEB-CLIENT-004 | Site pin and geofence | web | client | 5 | P0 | FR-04 | 6 | [spec](../02-screens/stage-05-client-setup/web-client-004-site-geofence/spec.md) |
| WEB-CLIENT-005 | BoQ review and approval | web | client | 5 | P0 | FR-05 | 5 | [spec](../02-screens/stage-05-client-setup/web-client-005-boq-review/spec.md) |
| WEB-CLIENT-006 | Quote checker | web | client | 5 | P0 | FR-17, FR-05 | 5 | [spec](../02-screens/stage-05-client-setup/web-client-006-quote-checker/spec.md) |
| WEB-CLIENT-007 | Fund the first milestone | web | client | 5 | P0 | FR-13 | 7 | [spec](../02-screens/stage-05-client-setup/web-client-007-fund-first-milestone/spec.md) |
| WEB-CLIENT-008 | Home: needs your attention | web | client | 6 | P0 | FR-15 | 2 | [spec](../02-screens/stage-06-client-dashboard-evidence/web-client-008-home/spec.md) |
| WEB-CLIENT-009 | Project overview | web | client | 6 | P0 | FR-15, FR-11, FR-18 | 2 | [spec](../02-screens/stage-06-client-dashboard-evidence/web-client-009-project-overview/spec.md) |
| WEB-CLIENT-010 | Evidence gallery | web | client | 6 | P0 | FR-06, FR-07, FR-08, FR-09, FR-10, FR-15 | 4 | [spec](../02-screens/stage-06-client-dashboard-evidence/web-client-010-evidence-gallery/spec.md) |
| WEB-CLIENT-011 | Evidence detail | web | client | 6 | P0 | FR-07, FR-08, FR-10 | 5 | [spec](../02-screens/stage-06-client-dashboard-evidence/web-client-011-evidence-detail/spec.md) |
| WEB-CLIENT-012 | Project site map | web | client | 6 | P0 | FR-04 | 2 | [spec](../02-screens/stage-06-client-dashboard-evidence/web-client-012-site-map/spec.md) |
| WEB-CLIENT-013 | Milestone detail (every state) | web | client | 7 | P0 | FR-12, FR-14, FR-15 | 8 | [spec](../02-screens/stage-07-client-milestones-money/web-client-013-milestone-detail/spec.md) |
| WEB-CLIENT-014 | Approve a release | web | client | 7 | P0 | FR-14, FR-15 | 7 | [spec](../02-screens/stage-07-client-milestones-money/web-client-014-approve-release/spec.md) |
| WEB-CLIENT-015 | Raise a dispute and outcomes | web | client | 7 | P0 | FR-14 | 7 | [spec](../02-screens/stage-07-client-milestones-money/web-client-015-dispute/spec.md) |
| WEB-CLIENT-016 | Fund the next milestone | web | client | 7 | P0 | FR-13 | 1 | [spec](../02-screens/stage-07-client-milestones-money/web-client-016-fund-next-milestone/spec.md) |
| WEB-CLIENT-017 | Ledger | web | client | 7 | P0 | FR-13, FR-23 | 2 | [spec](../02-screens/stage-07-client-milestones-money/web-client-017-ledger/spec.md) |
| WEB-CLIENT-018 | Weekly reports | web | client | 7 | P0 | FR-18 | 4 | [spec](../02-screens/stage-07-client-milestones-money/web-client-018-weekly-reports/spec.md) |
| WEB-CLIENT-019 | Material orders | web | client | 7 | P1 | FR-16, FR-17 | 4 | [spec](../02-screens/stage-07-client-milestones-money/web-client-019-material-orders/spec.md) |
| WEB-CLIENT-020 | Notifications | web | client | 7 | P1 | FR-20 | 2 | [spec](../02-screens/stage-07-client-milestones-money/web-client-020-notifications/spec.md) |
| WEB-CLIENT-021 | Live walkthrough (coming soon) | web | client | 7 | P2 | FR-21 | 2 | [spec](../02-screens/stage-07-client-milestones-money/web-client-021-live-walkthrough/spec.md) |
| WEB-CLIENT-022 | Land and title verification (coming soon) | web | client | 7 | P2 | FR-22 | 1 | [spec](../02-screens/stage-07-client-milestones-money/web-client-022-land-verification/spec.md) |
| WEB-CONTRACTOR-003 | Projects dashboard | web | contractor | 8 | P0 | FR-03, FR-12 | 1 | [spec](../02-screens/stage-08-contractor/web-contractor-003-dashboard/spec.md) |
| WEB-CONTRACTOR-004 | BoQ editor | web | contractor | 8 | P0 | FR-05 | 3 | [spec](../02-screens/stage-08-contractor/web-contractor-004-boq-editor/spec.md) |
| WEB-CONTRACTOR-005 | Milestones and claim | web | contractor | 8 | P0 | FR-12 | 3 | [spec](../02-screens/stage-08-contractor/web-contractor-005-milestones-claim/spec.md) |
| WEB-CONTRACTOR-006 | Rework and dispute | web | contractor | 8 | P0 | FR-12, FR-14 | 4 | [spec](../02-screens/stage-08-contractor/web-contractor-006-rework-dispute/spec.md) |
| WEB-CONTRACTOR-007 | Material requests | web | contractor | 8 | P1 | FR-16, FR-17 | 2 | [spec](../02-screens/stage-08-contractor/web-contractor-007-material-requests/spec.md) |
| WEB-CONTRACTOR-008 | Payouts | web | contractor | 8 | P1 | FR-14 | 1 | [spec](../02-screens/stage-08-contractor/web-contractor-008-payouts/spec.md) |
| WEB-CONTRACTOR-009 | Profile and track record | web | contractor | 8 | P1 | FR-01 | 1 | [spec](../02-screens/stage-08-contractor/web-contractor-009-profile/spec.md) |
| AND-CONTRACTOR-002 | Projects and claim (Android) | android | contractor | 8 | P0 | FR-12, FR-03 | 3 | [spec](../02-screens/stage-08-contractor/and-contractor-002-projects-claim/spec.md) |
| AND-CONTRACTOR-003 | Contractor capture | android | contractor | 8 | P0 | FR-06, FR-07, FR-08 | 2 | [spec](../02-screens/stage-08-contractor/and-contractor-003-contractor-capture/spec.md) |
| AND-CONTRACTOR-004 | Orders (Android) | android | contractor | 8 | P1 | FR-16 | 1 | [spec](../02-screens/stage-08-contractor/and-contractor-004-orders/spec.md) |
| AND-CONTRACTOR-005 | Alerts (Android) | android | contractor | 8 | P1 | FR-20 | 1 | [spec](../02-screens/stage-08-contractor/and-contractor-005-alerts/spec.md) |
| AND-SUPERVISOR-004 | Assigned projects and checklist | android | supervisor | 9 | P0 | FR-03, FR-12 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-004-projects-checklist/spec.md) |
| AND-SUPERVISOR-005 | Arrival check | android | supervisor | 9 | P0 | FR-08 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-005-arrival-check/spec.md) |
| AND-SUPERVISOR-006 | Capture | android | supervisor | 9 | P0 | FR-06, FR-07, FR-08 | 5 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-006-capture/spec.md) |
| AND-SUPERVISOR-007 | Sync queue | android | supervisor | 9 | P0 | FR-09, FR-08, FR-10 | 4 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-007-sync-queue/spec.md) |
| AND-SUPERVISOR-008 | Verify or send back | android | supervisor | 9 | P0 | FR-12, FR-14 | 4 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-008-verify/spec.md) |
| AND-SUPERVISOR-009 | Confirm delivery | android | supervisor | 9 | P1 | FR-16 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-009-confirm-delivery/spec.md) |
| AND-SUPERVISOR-010 | Spot checks | android | supervisor | 9 | P1 | FR-11 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-010-spot-checks/spec.md) |
| AND-SUPERVISOR-011 | Weekly report review | android | supervisor | 9 | P0 | FR-18 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-011-report-review/spec.md) |
| AND-SUPERVISOR-012 | Me, device and system states | android | supervisor | 9 | P0 | FR-02, FR-07 | 3 | [spec](../02-screens/stage-09-supervisor-android/and-supervisor-012-me-device/spec.md) |
| WEB-SUPPLIER-002 | Supplier dashboard | web | supplier | 10 | P1 | FR-16, FR-17 | 2 | [spec](../02-screens/stage-10-supplier/web-supplier-002-dashboard/spec.md) |
| WEB-SUPPLIER-003 | Incoming orders | web | supplier | 10 | P1 | FR-16 | 2 | [spec](../02-screens/stage-10-supplier/web-supplier-003-orders/spec.md) |
| WEB-SUPPLIER-004 | Order detail, delivery and payment | web | supplier | 10 | P1 | FR-16 | 3 | [spec](../02-screens/stage-10-supplier/web-supplier-004-order-detail/spec.md) |
| WEB-SUPPLIER-005 | Payouts history | web | supplier | 10 | P1 | FR-16 | 2 | [spec](../02-screens/stage-10-supplier/web-supplier-005-payouts/spec.md) |
| WEB-SUPPLIER-006 | Business profile and bank | web | supplier | 10 | P1 | FR-16 | 2 | [spec](../02-screens/stage-10-supplier/web-supplier-006-profile/spec.md) |
| WEB-SUPPLIER-007 | Price list contribution | web | supplier | 10 | P1 | FR-17 | 2 | [spec](../02-screens/stage-10-supplier/web-supplier-007-price-list/spec.md) |
| WA-SUPPLIER-001 | WhatsApp order notification | whatsapp | supplier | 10 | P1 | FR-16, FR-20 | 1 | [spec](../02-screens/stage-10-supplier/wa-supplier-001-whatsapp-order/spec.md) |
| WEB-OPS-002 | Overview, live map and money alerts | web | ops | 11 | P0 | FR-19, FR-14, FR-23 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-002-overview/spec.md) |
| WEB-OPS-003 | Supervisor vetting | web | ops | 11 | P0 | FR-02, FR-19 | 2 | [spec](../02-screens/stage-11-ops-console/web-ops-003-vetting/spec.md) |
| WEB-OPS-004 | Projects, BoQ approval and rotation | web | ops | 11 | P0 | FR-03, FR-04, FR-05, FR-11, FR-19 | 3 | [spec](../02-screens/stage-11-ops-console/web-ops-004-projects/spec.md) |
| WEB-OPS-005 | Flagged evidence review | web | ops | 11 | P0 | FR-10, FR-19 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-005-flagged-evidence/spec.md) |
| WEB-OPS-006 | Disputes and two-approver resolution | web | ops | 11 | P0 | FR-14, FR-19, FR-23 | 2 | [spec](../02-screens/stage-11-ops-console/web-ops-006-disputes/spec.md) |
| WEB-OPS-007 | Spot-check scheduler | web | ops | 11 | P1 | FR-11, FR-19 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-007-spot-checks/spec.md) |
| WEB-OPS-008 | Supplier verification | web | ops | 11 | P1 | FR-16 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-008-suppliers/spec.md) |
| WEB-OPS-009 | Price index management | web | ops | 11 | P0 | FR-17 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-009-price-index/spec.md) |
| WEB-OPS-010 | Weekly report review (ops) | web | ops | 11 | P0 | FR-18 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-010-report-review/spec.md) |
| WEB-OPS-011 | Audit log and agent runs | web | ops | 11 | P0 | FR-23 | 2 | [spec](../02-screens/stage-11-ops-console/web-ops-011-audit/spec.md) |
| WEB-OPS-012 | Users and status | web | ops | 11 | P1 | FR-01, FR-23 | 1 | [spec](../02-screens/stage-11-ops-console/web-ops-012-users/spec.md) |
| WA-CLIENT-001 | Client WhatsApp messages | whatsapp | client | 12 | P1 | FR-20, FR-18 | 2 | [spec](../02-screens/stage-12-cross-cutting/wa-client-001-whatsapp-messages/spec.md) |
| AND-SUPERVISOR-013 | Spot check SMS and push | android | supervisor | 12 | P1 | FR-20, FR-11 | 1 | [spec](../02-screens/stage-12-cross-cutting/and-supervisor-013-spot-check-sms-push/spec.md) |
| EMAIL-CLIENT-001 | Client emails | email | client | 12 | P1 | FR-20, FR-18 | 2 | [spec](../02-screens/stage-12-cross-cutting/email-client-001-emails/spec.md) |
| AND-SUPERVISOR-014 | Supervisor push notifications | android | supervisor | 12 | P1 | FR-20 | 1 | [spec](../02-screens/stage-12-cross-cutting/and-supervisor-014-push/spec.md) |
| AND-CONTRACTOR-006 | Contractor push notifications | android | contractor | 12 | P1 | FR-20 | 1 | [spec](../02-screens/stage-12-cross-cutting/and-contractor-006-push/spec.md) |
| WA-CLIENT-002 | WhatsApp assistant | whatsapp | client | 12 | P1 | FR-20 | 2 | [spec](../02-screens/stage-12-cross-cutting/wa-client-002-whatsapp-assistant/spec.md) |
| WEB-CLIENT-023 | Client settings | web | client | 12 | P1 | FR-20, FR-01 | 3 | [spec](../02-screens/stage-12-cross-cutting/web-client-023-settings/spec.md) |
| WEB-CONTRACTOR-010 | Devices and revoke | web | contractor | 12 | P0 | FR-07 | 1 | [spec](../02-screens/stage-12-cross-cutting/web-contractor-010-devices/spec.md) |
| WEB-OPS-013 | Ops profile, alerts and security | web | ops | 12 | P1 | FR-20 | 1 | [spec](../02-screens/stage-12-cross-cutting/web-ops-013-settings/spec.md) |
| AND-SUPERVISOR-015 | Supervisor settings and revoke | android | supervisor | 12 | P0 | FR-07, FR-20 | 2 | [spec](../02-screens/stage-12-cross-cutting/and-supervisor-015-settings/spec.md) |
| WEB-SUPPLIER-008 | Supplier notification settings | mobile-web | supplier | 12 | P1 | FR-20 | 1 | [spec](../02-screens/stage-12-cross-cutting/web-supplier-008-settings/spec.md) |
| WEB-CLIENT-024 | System states (web) | web | client | 12 | P0 | FR-01 | 11 | [spec](../02-screens/stage-12-cross-cutting/web-client-024-system-states/spec.md) |
| AND-SUPERVISOR-016 | System states (Android) | android | supervisor | 12 | P0 | FR-01, FR-06 | 9 | [spec](../02-screens/stage-12-cross-cutting/and-supervisor-016-system-states/spec.md) |
| WEB-CLIENT-025 | Empty states (client) | web | client | 12 | P0 | FR-15 | 6 | [spec](../02-screens/stage-12-cross-cutting/web-client-025-empty-states/spec.md) |
| WEB-CONTRACTOR-011 | Empty states (contractor) | web | contractor | 12 | P0 | FR-12 | 3 | [spec](../02-screens/stage-12-cross-cutting/web-contractor-011-empty-states/spec.md) |
| AND-SUPERVISOR-017 | Empty states (supervisor) | android | supervisor | 12 | P0 | FR-09 | 3 | [spec](../02-screens/stage-12-cross-cutting/and-supervisor-017-empty-states/spec.md) |
| WEB-SUPPLIER-009 | Empty states (supplier) | web | supplier | 12 | P1 | FR-16 | 2 | [spec](../02-screens/stage-12-cross-cutting/web-supplier-009-empty-states/spec.md) |
| WEB-OPS-014 | Empty states (ops) | web | ops | 12 | P0 | FR-19 | 2 | [spec](../02-screens/stage-12-cross-cutting/web-ops-014-empty-states/spec.md) |

## Stage 1 inventory → package screens

How each row of the Stage 1 screen inventory (98 rows) maps to the package. "Not designed" rows are listed again in PACKAGE-REPORT.md.

| Stage 1 ID | Stage 1 screen | Priority | Package screens |
|---|---|---|---|
| DS-01 | Design system: tokens, components, iBackHome patterns, Android components | P0 | Design system → 01-design-system/ (not a screen) |
| PUB-01 | Landing page: the problem, proof + escrow promise, sign-up | P1* | WEB-PUBLIC-001 |
| PUB-02 | How it works: evidence checks, two-key release, licensed escrow | P1* | WEB-PUBLIC-002 |
| PUB-03 | Pricing (placeholder figures until week-one interviews) | P1* | WEB-PUBLIC-003 |
| PUB-04 | Become a supervisor: requirements, apply | P1* | WEB-PUBLIC-004, WEB-PUBLIC-005 |
| PUB-05 | Privacy policy and terms (NDPA) | P0 | WEB-PUBLIC-006, WEB-PUBLIC-007, WEB-PUBLIC-008, WEB-PUBLIC-009 |
| AU-01 | Sign in with phone or email | P0 | WEB-PUBLIC-010, AND-PUBLIC-001, WEB-OPS-001 |
| AU-02 | Enter 6-digit code: expiry, resend, switch channel, errors | P0 | WEB-PUBLIC-010, AND-PUBLIC-001, WEB-OPS-001 |
| AU-03 | Code message | P0 | **Not designed as its own screen.** Code message copy (WhatsApp/SMS/email) is described on the sign-in board only. |
| AU-04 | First-time profile: name, country, time zone, consent | P0 | WEB-CLIENT-001, WEB-CONTRACTOR-002, AND-CONTRACTOR-001, WEB-SUPPLIER-001 |
| AU-05 | Accept invitation to a project or role | P0 | WA-CONTRACTOR-001, WEB-CONTRACTOR-001, WEB-SUPPLIER-001 |
| AU-06 | Android permissions (camera, location) and device key registration | P0 | AND-SUPERVISOR-002 |
| AU-07 | Supervisor vetting application: registration, NIN, guarantors, relatives | P0 | AND-SUPERVISOR-001 |
| AU-08 | Vetting status: pending, approved, rejected with reason | P0 | AND-SUPERVISOR-001 |
| CS-01 | My projects: list and first-run empty state | P0 | WEB-CLIENT-003 |
| CS-02 | New project: title, address, budget, currency | P0 | WEB-CLIENT-003 |
| CS-03 | Invite contractor by phone or email | P0 | WEB-CLIENT-003 |
| CS-04 | Pin the site and draw the geofence | P0 | WEB-CLIENT-004 |
| CS-05 | Set-up tracker: contractor, BoQ, supervisor, site, approvals | P0 | WEB-CLIENT-003 |
| CS-06 | BoQ review by milestone: totals vs budget, who has approved | P0 | WEB-CLIENT-005 |
| CS-07 | Quote check results: flagged lines, index price, % difference | P0 | WEB-CLIENT-006 |
| CS-08 | Approve BoQ or send back with reason | P0 | WEB-CLIENT-005 |
| CS-09 | Fund a milestone: summary, then Stripe Checkout, then return | P0 | WEB-CLIENT-007, WEB-CLIENT-016 |
| CS-10 | Funding pending until escrow confirms, then funded | P0 | WEB-CLIENT-007 |
| CD-01 | Project dashboard: progress vs plan, spend vs budget, next action | P0 | WEB-CLIENT-008, WEB-CLIENT-009 |
| CD-02 | Evidence gallery: filter by milestone, status, who captured | P0 | WEB-CLIENT-010 |
| CD-03 | Evidence detail: photo or video, three checks, time, site map | P0 | WEB-CLIENT-011, WEB-CLIENT-012 |
| CD-04 | Visits and spot-check history | P1 | WEB-CLIENT-009 |
| CD-05 | Live video walkthrough — coming soon | P2 | WEB-CLIENT-021 |
| CD-06 | Land and title verification — coming soon | P2 | WEB-CLIENT-022 |
| CM-01 | Milestones: progress strip and list | P0 | WEB-CLIENT-013 |
| CM-02 | Milestone detail: two-key release, evidence, checklist | P0 | WEB-CLIENT-013 |
| CM-03 | Approve release: confirm (under 3 taps) | P0 | WEB-CLIENT-014 |
| CM-04 | Raise dispute: reason, pause notice | P0 | WEB-CLIENT-015 |
| CM-05 | Dispute status and outcome | P0 | WEB-CLIENT-015 |
| CM-06 | Ledger: funding, releases, payouts, fees, FX per entry | P0 | WEB-CLIENT-017 |
| CM-07 | Approve material order (with quote check) | P1 | WEB-CLIENT-019 |
| CM-08 | Weekly reports list | P0 | WEB-CLIENT-018 |
| CM-09 | Weekly report: web view and PDF | P0 | WEB-CLIENT-018 |
| CM-10 | Weekly report summary message | P0 | WA-CLIENT-001 |
| CM-11 | WhatsApp assistant: questions, answers, hand-off to ops | P1 | WA-CLIENT-002 |
| CO-01 | My projects, including pending invitations | P0 | WEB-CONTRACTOR-003, AND-CONTRACTOR-002 |
| CO-02 | Project overview: milestones, what is next, payments | P0 | WEB-CONTRACTOR-003, AND-CONTRACTOR-002 |
| CO-03 | BoQ editor: lines grouped into milestones, totals, submit | P0 | WEB-CONTRACTOR-004 |
| CO-04 | BoQ status: approvals, sent back with reason | P0 | WEB-CONTRACTOR-004 |
| CO-05 | Claim milestone | P0 | WEB-CONTRACTOR-005, AND-CONTRACTOR-002 |
| CO-06 | Contractor capture (labelled as contractor evidence) | P0 | AND-CONTRACTOR-003 |
| CO-07 | Rework needed: supervisor rejection or dispute outcome | P0 | WEB-CONTRACTOR-006 |
| CO-08 | Raise or follow a dispute | P0 | WEB-CONTRACTOR-006 |
| CO-09 | Request materials: supplier, items from price index | P1 | WEB-CONTRACTOR-007 |
| CO-10 | Material orders and status | P1 | WEB-CONTRACTOR-007, AND-CONTRACTOR-004 |
| CO-11 | Price index (read only) | P0 | WEB-CONTRACTOR-007 |
| CO-12 | Payments received (NGN) | P1 | WEB-CONTRACTOR-008 |
| SV-01 | Assigned sites, with sync status | P0 | AND-SUPERVISOR-004 |
| SV-02 | Site detail: milestones, checklists, recent captures | P0 | AND-SUPERVISOR-004, AND-SUPERVISOR-005 |
| SV-03 | Capture: in-app camera, geofence bar, photo or video | P0 | AND-SUPERVISOR-006 |
| SV-04 | Capture review: add note, attach to milestone | P0 | AND-SUPERVISOR-006 |
| SV-05 | Upload queue: queued, uploading, results | P0 | AND-SUPERVISOR-007 |
| SV-06 | Capture result: accepted, flagged, rejected with reason | P0 | AND-SUPERVISOR-007 |
| SV-07 | Verify milestone: checklist with required evidence | P0 | AND-SUPERVISOR-008 |
| SV-08 | Reject milestone with reason (rework) | P0 | AND-SUPERVISOR-008 |
| SV-09 | Review weekly report draft, mark reviewed | P0 | AND-SUPERVISOR-011 |
| SV-10 | Blocking states: mock location, weak GPS, clock drift, 48 h warning | P0 | AND-SUPERVISOR-005, AND-SUPERVISOR-006, AND-SUPERVISOR-007 |
| SV-11 | Spot checks to do | P1 | AND-SUPERVISOR-010 |
| SV-12 | Complete spot check: captures and findings | P1 | AND-SUPERVISOR-010 |
| SV-13 | Confirm material delivery: quantities and photos | P1 | AND-SUPERVISOR-009 |
| SU-01 | Orders: approved, delivered, paid, cancelled | P1 | WEB-SUPPLIER-002, WEB-SUPPLIER-003 |
| SU-02 | Order detail: items, quantities, site location, contact | P1 | WEB-SUPPLIER-004 |
| SU-03 | Delivery confirmation (view) and payment status | P1 | WEB-SUPPLIER-004, WEB-SUPPLIER-005 |
| SU-04 | Payout bank details | P1 | WEB-SUPPLIER-006 |
| SU-05 | New order and payment messages | P1 | WA-SUPPLIER-001 |
| OP-01 | Work queue: vetting, flagged evidence, disputes, alerts | P0 | WEB-OPS-002 |
| OP-02 | Supervisor vetting detail: checks, guarantors, relatives, decide | P0 | WEB-OPS-003 |
| OP-03 | Projects list and project detail (ops view) | P0 | WEB-OPS-004 |
| OP-04 | Assign supervisor: relation conflicts, rotation | P0 | WEB-OPS-004 |
| OP-05 | Approve BoQ (ops) | P0 | WEB-OPS-004 |
| OP-06 | Edit site or geofence; pause and resume project | P0 | WEB-OPS-004 |
| OP-07 | Flagged evidence review: side-by-side match, decide | P0 | WEB-OPS-005 |
| OP-08 | Dispute review and resolution (two ops approvals) | P0 | WEB-OPS-006 |
| OP-09 | Live map of sites | P0 | WEB-OPS-002 |
| OP-10 | Weekly report review (ops) | P0 | WEB-OPS-010 |
| OP-11 | Money alerts: failed releases, reconciliation mismatches | P0 | WEB-OPS-002 |
| OP-12 | Audit log search | P0 | WEB-OPS-011 |
| OP-13 | Price index management | P0 | WEB-OPS-009 |
| OP-14 | Spot-check scheduler | P1 | WEB-OPS-007 |
| OP-15 | Suppliers: add, verify, payout details | P1 | WEB-OPS-008 |
| OP-16 | AI agent run log | P1 | WEB-OPS-011 |
| NS-01 | Invitation messages | P0 | WA-CONTRACTOR-001 |
| NS-02 | Client messages: claimed, verified, released, reminder | P1 | WEB-CLIENT-020, WA-CLIENT-001 |
| NS-03 | Client emails: verified, released, dispute, weekly report | P1 | WEB-CLIENT-020, EMAIL-CLIENT-001 |
| NS-04 | Contractor messages: verified, released, dispute | P1 | AND-CONTRACTOR-005, AND-CONTRACTOR-006 |
| NS-05 | Supervisor alerts: claim, flag, spot check, report to review | P1 | AND-SUPERVISOR-013, AND-SUPERVISOR-014 |
| NS-06 | Ops email alerts | P1 | WEB-OPS-013 |
| NS-07 | Account settings: profile, time zone, channel order | P1 | WEB-CLIENT-023, WEB-OPS-013, AND-SUPERVISOR-015, WEB-SUPPLIER-008 |
| NS-08 | Devices: view and revoke signing key | P0 | AND-SUPERVISOR-012, WEB-CONTRACTOR-010, AND-SUPERVISOR-015 |
| NS-09 | Privacy and data: consent, policy link | P0 | WEB-CLIENT-023 |
| NS-10 | System states: empty, loading, 403, 404, 409 conflict, expired session, offline | P0 | WEB-OPS-001, WEB-CLIENT-002, AND-SUPERVISOR-003, AND-SUPERVISOR-012, WEB-CLIENT-024, AND-SUPERVISOR-016, WEB-CLIENT-025, WEB-CONTRACTOR-011, AND-SUPERVISOR-017, WEB-SUPPLIER-009, WEB-OPS-014 |
| QA-01 | Clickable prototype of all P0 flows; accessibility and consistency pass | P0 | Stage 13 prototypes → 03-prototype-flows/ (not a screen) |

Screens added after Stage 1 (no Stage 1 row): WEB-CONTRACTOR-009 Profile and track record, WEB-SUPPLIER-007 Price list contribution, WEB-OPS-012 Users and status.
