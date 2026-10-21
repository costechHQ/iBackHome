# Error codes → UI

Every error code in the Spec, plus the HTTP classes and the device-side refusals the designs handle. Error body shape (Spec): `{"error": {"code": "...", "message": "..."}}`. Show designed copy, never the raw message.

| Code | HTTP | Screen (ID and frame) | Message text on the design | Component |
|---|---|---|---|---|
| `pin_outside_geofence` | 422 | WEB-CLIENT-004 Site pin and geofence (frame "Error — pin outside the boundary") | "The pin is outside the boundary. Move the pin onto the plot, or redraw the boundary to include it." Save is blocked; step "Pin on your plot" shows "Currently outside the boundary". | Alert (bad) above the map + checklist row |
| `site_locked` | 409 | WEB-CLIENT-004 (frame "Locked — project active"); WEB-OPS-004 for ops edits | "This site is locked. It was fixed when the BoQ was approved, so evidence rules can't change mid-build. Our team can update it if the plot really changed." Button: "Ask our team to change it". | Locked chip + neutral alert; map read-only |
| `boq_total_mismatch` | 422 | WEB-CONTRACTOR-004 BoQ editor (frame "Editing version 2 · validation errors") | Error summary "Fix 3 things before you submit" with per-line messages; contract sum field: "Doesn't match the lines total. ₦395,000 apart." Line totals are always shown as "worked out by iBackHome". | Error summary alert + field errors |
| `site_not_set` | 409 | WEB-CLIENT-005 BoQ review; WEB-OPS-004 ops BoQ approval | Prevented in the UI: the approvals list shows "Site saved — required before the final approval". If the server still returns it, show an alert linking to the site screen. (**Error state not separately designed.**) | Checklist row; fallback alert (bad) |
| `milestone_not_verified` | 409 | WEB-CLIENT-014 Approve a release; WEB-CLIENT-024 409 frame | Approve only renders in the verified state. If the milestone moved, use the 409 conflict page: "Roofing was already approved — You approved it on your phone at 09:12 GMT, so nothing was sent twice." Buttons "See release status", "Back to project". | 409 conflict page |
| `notifications_not_configured` | 503 | WEB-PUBLIC-010 Sign in (card "Channel unavailable · Server: 503"); AND-PUBLIC-001 | Says the chosen channel is unavailable and offers the other channels; never switches silently. | AuthCard state channelDown |
| `notification_failed` | 502 | WEB-PUBLIC-010 Sign in (card "Send failed · Server: 502") | "We couldn't send your code by SMS." with retry and other channels. | AuthCard state sendFailed |
| OTP wrong code (no code in Spec) | — (assume 400/401) | WEB-PUBLIC-010 card "Wrong code" | "That code isn't right. Check the latest message and try again." + attempts left. | AuthCard otpWrong |
| OTP too many attempts (no code in Spec) | — (assume 429) | WEB-PUBLIC-010 card "Too many attempts" | Code cancelled after 5 attempts; request a new one. | AuthCard otpLocked |
| OTP expired (no code in Spec) | — (assume 400/410) | WEB-PUBLIC-010 card "Code expired" | After 5 minutes; send a new code. | AuthCard otpExpired |
| OTP rate limited (no code in Spec) | — (assume 429) | WEB-PUBLIC-010 card "Rate limited" | Per number and device; shows when to try again ([10 minutes]). | AuthCard rateLimited |
| 409 invalid state transition (any) | 409 | WEB-CLIENT-024 409 page; AND-SUPERVISOR-008 "Conflict · changed while offline"; WEB-CONTRACTOR-005 claim; WEB-CLIENT-015 dispute | Web: "<thing> was already <done>" + what happened, nothing sent twice. Android: "Blockwork changed while you were offline. Your verification wasn't recorded." The evidence still uploads. | Conflict page / Android conflict screen |
| 409 idempotent replay | 409/200 | WEB-CLIENT-024 409 frame ("Error 409 · same request recognised") | Treat a replayed Idempotency-Key as success; show the existing result. | Conflict page |
| 401 expired / invalid token | 401 | WEB-CLIENT-002, WEB-OPS-001, AND-SUPERVISOR-003 | Try `POST /auth/refresh` silently; if it fails: "Please sign in again" and return to the same page. Android: queued captures are safe. | Session-expired dialog / bottom sheet |
| 403 forbidden (role or project membership) | 403 | WEB-CLIENT-024 "Permission denied · 403"; AND-SUPERVISOR-016 "Not allowed · rotated off" | "This page is only for the client. You're signed in as Engr. Obi (contractor)…" with a link to the right place. | Error page |
| 404 not found | 404 | WEB-CLIENT-024 "404 · page not found" | "We can't find that page. The link may be old… Your projects and money aren't affected." | Error page |
| 5xx server error | 500 | WEB-CLIENT-024 "500"; AND-SUPERVISOR-016 "Server error" | "Something went wrong on our side. Nothing was charged, approved or released." + reference ID. | Error page |
| Validation (422) generic | 422 | WEB-CLIENT-024 "Form validation"; AND-SUPERVISOR-016 | Error summary listing fixes, field-level messages, focus moved to the summary. | Error summary + field error |
| Evidence rejected (status, not an HTTP error) | — | AND-SUPERVISOR-007 "Rejected capture · reason" | Shows which check failed, e.g. "62 m outside, beyond the 25 m allowance", and what to do. | Sync row + three-checks list |
| Capture refused on device (not an HTTP error) | — | AND-SUPERVISOR-006 "Refused · GPS too weak", "Refused · mock location" | "GPS is too weak: ±72 m. We need ±50 m or better." | Camera blocking banner |
| Stripe payment failed / cancelled | — (Stripe redirect) | WEB-CLIENT-007 "Payment failed or cancelled" | Nothing charged; try again. | Alert + retry |
| Offline (web) | — | WEB-CLIENT-024 "Offline" | "You're offline. Showing what loaded at 14:02. Approvals and payments are paused until you're back." Approve button disabled. | Offline bar |

Codes for OTP failures, rate limits and generic validation are not named in the Spec; agree them with the backend and map them to the AuthCard states above.
