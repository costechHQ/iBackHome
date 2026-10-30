# mobile/

The Flutter Android app for supervisors and contractors (Android 8+, offline-first). Owner: Gabriel.
Designs: `Docs/design/` (screens `AND-*`). Roadmap: `Docs/iBackHome-Web-E2E-Test-Guide-and-Mobile-Roadmap.md`, Part B.

## What works (stages M1 to M5, first cut)

| Area | Where |
| --- | --- |
| Sign in with OTP (phone by SMS or WhatsApp, or email), consent, role gate | `lib/features/sign_in_screen.dart`, `lib/core/services.dart` |
| Tokens in encrypted storage; one refresh at a time, never retried blindly | `lib/core/api.dart`, `lib/core/token_store.dart` |
| ECDSA P-256 key in the Android Keystore, registered with `POST /devices` | `android/.../MainActivity.kt`, `lib/core/signing.dart` |
| In-app camera only (no gallery, no `image_picker`), GPS and clock stamp, arrival warning | `lib/features/capture_screen.dart`, `lib/core/geo.dart` |
| Compress (1600 px, JPEG q80), SHA-256, sign exactly the uploaded bytes | `lib/core/capture_service.dart` |
| Offline queue (SQLite), upload with `Idempotency-Key`, backoff 5 s to 10 min, status per capture | `lib/core/queue_db.dart`, `lib/core/sync_service.dart`, `lib/features/queue_screen.dart` |
| Projects, milestones, contractor claim, supervisor verify or send back | `lib/features/project_screen.dart`, `lib/features/verify_screen.dart` |

The signing format is the backend contract in `backend/app/features/evidence/SIGNING.md`;
`test/signing_test.dart` pins its test vector. Change both together.

## Run it

From `mobile/` in Git Bash. Start the backend first (`docker compose up` in the repo root, then `uv run python scripts/seed.py` in `backend/`).

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

## Not done yet

- Video capture (needs the backend to strip MP4 metadata first), WorkManager background upload (the queue syncs while the app is open, on reconnect and on resume).
- Verification and claim are online only; the roadmap wants them queued offline.
- The local database is not encrypted (the files are signed, so tampering is caught by the server).
- Spot checks, delivery confirmation, weekly report review, device revoke, FCM push, Play Integrity, crash reporting.
- Inter and JetBrains Mono fonts: the design handoff has `.woff2` only; Flutter needs `.ttf`, so the system font is used for now.
- Release signing and Play Console. Not yet run on a real device or emulator.
