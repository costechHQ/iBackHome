# State → UI

Every state machine in the Spec mapped to the chip label, tone (token pair in tokens.json → status) and the actions each role may take. Build these labels and tones once (status chip component) and use them everywhere. Any action not listed is hidden, not disabled, unless the design shows it disabled with a reason. An invalid transition returns 409 (see error-codes-to-ui.md).

Tones: ok `#E7F4EC/#1E6B45` · warn `#FDF1D8/#8A5300` · bad `#FDECEA/#B42318` · neutral `#EEF1F5/#4A5363` · info `#E8EFFC/#2552B0`.

## Milestone

Stepper node shapes: released/approved navy fill + check · verified accent ring + check · claimed amber ring + hand · funded navy ring + lock · pending dashed ring + number · disputed red ring + scales.

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `pending` | Pending (neutral); amount shown as "≈ £ estimate" | all parties | Client: Fund this milestone (once the previous one is released; funding ahead allowed). Others: none. |
| `funded` | Funded (neutral) | all parties | Contractor: Claim milestone (project active). Contractor: request materials against it. Client: none. |
| `claimed` | Claimed (warn) · "Waiting for the supervisor" | all parties | Supervisor (assigned): Verify or Send back with reasons. Client: read-only, no approve or dispute. Contractor: upload contractor evidence (does not count). |
| `verified` | Verified (info) · "Needs your approval" | all parties | Client: Approve release (3 taps on mobile) or Raise a dispute. Others: none. |
| `approved` | Approved (info) · "Releasing £…" | all parties | None (system waits for escrow confirmation; alert after [1 hour]). |
| `disputed` | Disputed (bad) · "Release paused · under review by iBackHome" | all parties | Ops: propose outcome, second ops approves release (two approvers) or rework (one). Client/contractor: view dispute. |
| `released` | Released (ok) | all parties | Client: View receipt, Download PDF. Contractor: see payout. |

Supervisor rejection (claimed → funded) shows to the contractor as "Sent back · rework needed" with the reasons; the client sees "Funded · rework" (neutral) in ops lists.

## Evidence

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `pending_checks` | Checking (neutral); on the phone: Queued / Uploading (neutral) | capturer, ops | Supervisor app: retry upload. Nobody can decide yet. |
| `accepted` | Accepted (ok); contractor uploads add an outlined "Contractor" label | all parties | None. Counts toward verification only if captured by the supervisor. |
| `flagged` | Client: "Under review by iBackHome" (warn). Supervisor and ops: "Flagged" (warn) | all parties | Ops: Accept or Reject (reject needs notes). A flag never rejects a milestone by itself. |
| `rejected` | Rejected (bad) with the reason (outside geofence, bad signature, clock drift, upload window) | capturer, ops | Supervisor: capture again. Clients do not see rejected captures. |

## Project

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `draft` | Draft (neutral) / "Setup" in ops lists | parties, ops | Client: invite contractor, set site. Contractor: submit BoQ. |
| `boq_review` | BoQ review (warn) / "In review" (info) on the contractor's BoQ | parties, ops | Client, contractor, ops: approve or send back with reason (MX-08). Client: change site. |
| `active` | Active (info) | parties, ops | Normal work. Ops: pause (MX-09), edit locked site with reason. |
| `paused` | Paused (neutral) + banner with the reason | parties, ops | Claims, captures and approvals disabled. Ops: resume. |
| `completed` | Completed (ok) | parties, ops | Read-only; reports and ledger kept. |

## Escrow release

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `requested` | "Releasing" / Approved (info) | client, contractor, ops | None. |
| `submitted` | "Sent to the escrow partner" (timeline step) | client, ops | None. |
| `released` | Released (ok) + receipt R-xxxx | all parties | View receipt. |
| `failed` | Client: "Still confirming — your money is safe". Ops: "Release failed" (bad), "Retried 3 times" | client (soft), ops | Ops: Retry release (MX-21). Retries 3 times automatically first. |

## Dispute

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `open` | Disputed (bad) on the milestone; ops queue: "Waiting for 2nd approver" (warn) after a proposal | client, contractor, ops | Ops: propose; a different ops user approves. While open, no release can be requested. |
| `resolved_release` | Outcome A · released (ok) | client, contractor, ops | None; release proceeds. |
| `resolved_reject` | Outcome B · rework required (warn on the contractor side) | client, contractor, ops | Contractor: rework and claim again. |

## Material order

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `requested` | Needs your approval (warn) for the client; "Requested" for the contractor | client, contractor | Client: Approve or Decline with reason. Supplier does not see it yet. |
| `approved` | Approved by client (ok) / "To deliver" (neutral) for the supplier | client, contractor, supplier, supervisor | Supervisor: confirm delivery with counts and photos. |
| `delivered` | Delivered (info) | all order parties | None; payment follows. |
| `paid` | Paid (ok) | all order parties | View payout. |
| `cancelled` | Cancelled (neutral) | all order parties | None. |
| `(not in Spec) on hold` | Payment on hold (warn) | supplier | **Design state with no Spec status**: delivery confirmed but the milestone is under review/dispute. Needs a backend decision (MX-05). |

## Weekly report

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `draft` | Draft (neutral) · "AI-generated draft"; "Draft · 2 days late" (warn) in ops | assigned supervisor, ops | Supervisor (assigned) or ops: Mark reviewed. The board also designs "Edit the draft" (MX-13, see conflict note). |
| `reviewed` | Reviewed (ok) · "Reviewed by <name>" | supervisor, ops | None; send job runs every 15 min. |
| `sent` | Shown to the client with "AI-generated" + "Reviewed by" | client, parties | Client: read, download PDF. |

## Supervisor vetting

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `pending` | In review / In vetting (info) | supervisor, ops | Ops: Approve (locked until all checks pass), Reject with reason, Ask for more information. |
| `approved` | Approved / Vetted (ok) | supervisor, ops | Ops can assign (unless related to the contractor). |
| `rejected` | Rejected, with reason (bad) | supervisor, ops | Supervisor: re-apply (PUT /supervisors/me/profile). |

## Payout

| State | Chip label (tone) | Who sees it | Allowed actions by role |
|---|---|---|---|
| `pending` | Held in escrow / Pending (neutral) | contractor or supplier | — |
| `success` | Paid (ok) | contractor or supplier | Download advice (PDF, MX-22). |
| `failed` | Failed (bad) | payee, ops | Ops follows up. |
| `reversed` | Reversed (bad) — not designed | payee, ops | **No design**; use the failed pattern. |

## Device-only states (supervisor app)

Queued, uploading, retrying, conflict (409 while offline) and "older than 48 h" warning are local sync-queue states, shown with neutral/warn chips in AND-SUPERVISOR-007. They are not server states.

## Tone inconsistencies found on the boards

- "Funded" appears as info on the Stage 5 funding success frame and as neutral everywhere else: use neutral.
- "Under review" is warn for evidence and bad for a dispute under review on the contractor's rework frame: keep warn for evidence; disputes use the Disputed (bad) chip.
- "Active" is info for projects and ok for user status in the ops user list: different entities; keep as designed.
