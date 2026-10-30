# mobile/

The Flutter Android app for supervisors and contractors (Android 8+, offline-first). Owner: Gabriel.
Designs: `Docs/design/` (screens `AND-*`). Roadmap: `Docs/iBackHome-Web-E2E-Test-Guide-and-Mobile-Roadmap.md`, Part B.

## What it does (against the PRD)

| PRD | Screen (design id) | Where |
| --- | --- | --- |
| FR-01 Sign in with OTP, roles | AND-PUBLIC-001, 003 | `features/sign_in_screen.dart`, `core/services.dart` |
| FR-02 Supervisor vetting | AND-SUPERVISOR-001 | `features/vetting_screen.dart` |
| FR-03, FR-12 Projects, milestones, claim, verify | AND-SUPERVISOR-004, 008, AND-CONTRACTOR-002 | `features/project_screen.dart`, `features/verify_screen.dart` |
| FR-06 In-app camera only (photo and video, no gallery) | AND-SUPERVISOR-002, 006, AND-CONTRACTOR-003 | `features/permissions_screen.dart`, `features/capture_screen.dart` |
| FR-07 Metadata signed on the device (ECDSA P-256 in the Keystore) | AND-SUPERVISOR-002 | `android/.../MainActivity.kt`, `core/signing.dart` |
| FR-08 Geofence arrival check (warns; the server decides) | AND-SUPERVISOR-005 | `features/arrival_screen.dart`, `core/capture_rules.dart` |
| FR-09 Offline capture, sync with original time and place | AND-SUPERVISOR-007 | `core/queue_db.dart`, `core/sync_service.dart`, `features/queue_screen.dart` |
| FR-10 Reuse check (server) shown as the three checks | AND-SUPERVISOR-007 | `core/capture_rules.dart` (`ThreeChecks`) |
| FR-11 Unannounced spot checks | AND-SUPERVISOR-010 | `features/spot_checks_screen.dart` |
| FR-18 Review and send the weekly AI report | AND-SUPERVISOR-011 | `features/reports_screen.dart` |
| Device and settings, revoke a phone | AND-SUPERVISOR-012, 015 | `features/home_screen.dart` (Me tab) |

Rules the app enforces on the device: refuses a capture when GPS accuracy is worse than 50 m or the
location is simulated; warns (but allows) outside the boundary; compresses photos to about 1600 px,
JPEG q80, then hashes and signs exactly the uploaded bytes; videos up to 60 s; captures keep their
original time and place; warns before the 72 h upload window ends; claims and verifications made
without signal are queued and sent with the same `Idempotency-Key` (a verification waits until its
photos are accepted). Errors use the wording in `Docs/design/04-api-mapping/error-codes-to-ui.md`.

The signing format is the backend contract in `backend/app/features/evidence/SIGNING.md`;
`test/signing_test.dart` pins its test vector. Change both together.

## Run it

From `mobile/` in Git Bash. Start the backend first (`docker compose up` in the repo root, then
`docker compose exec api python scripts/seed.py`). Seeded supervisor: `08030000002`; contractor: `08030000001`.

```bash
flutter pub get
flutter analyze
flutter test
# Android emulator (reaches the host as 10.0.2.2):
flutter run
# Real phone on the same Wi-Fi, using your PC's address:
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000/api/v1
# Debug APK:
flutter build apk --debug
```

Debug builds allow plain http (`android/app/src/debug/AndroidManifest.xml`); release builds do not, so staging needs https.
Locally the OTP code is printed in `docker compose logs api` (only when `ENVIRONMENT=local`).
A real phone is the right test for the camera, GPS and Keystore: emulators fake them.

## Blocked by the backend (not built, on purpose)

- **Confirm delivery (AND-SUPERVISOR-009) and contractor orders (AND-CONTRACTOR-004):** there is no route that lists a project's orders or deliveries, only `POST`. Needs `GET /projects/{id}/orders` (and a supplier-side list). Propose it, then build.
- **Push and in-app alerts (AND-SUPERVISOR-013/014, AND-CONTRACTOR-005/006, FR-20):** no route to register an FCM token or to list notifications, and no Firebase project yet.
- **Spot checks:** a supervisor doing a spot check is not a member of the project, so `GET /projects/{id}` is 403 (the app cannot read the site boundary) and the server's evidence check rejects their captures as "not a party to this project". The screens are built; the backend needs to let the visiting supervisor in for the visit.
- **Checklist templates (AND-SUPERVISOR-004):** the design says they come from ops templates; no route exists, so every milestone uses `defaultChecklist` in `features/capture_target.dart` (a placeholder).
- **Supervisor NIN:** the application API takes no NIN; operations verify it, and the app shows its status.
- **Weekly report edits:** the review route takes no body, so the app can mark a report reviewed but not edit it.
- **Revoking another phone:** there is no device list route, so a person can revoke only the phone in their hand.

## Not done yet

- WorkManager background upload (the queue syncs while the app is open, on reconnect and on resume).
- The local database is not encrypted (the files are signed, so tampering is caught by the server).
- Client-side video metadata is not stripped by the backend yet (MP4 can carry GPS); fix before the pilot.
- Play Integrity, crash reporting, release signing and Play Console; a low-storage warning.
- Not yet run on a real device. The emulator on the dev PC was too slow to finish a test.
- Signing out and signing in as a different person leaves the first person's queued captures on the phone; the server rejects them (wrong device owner). Clear them before handing a phone over.
