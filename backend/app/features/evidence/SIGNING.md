# Evidence signing format (contract for the Flutter phase)

Every photo or video is signed on the phone. The server rebuilds the same bytes from the metadata
you send and checks the signature. If one byte differs, the capture is rejected.
Code: `signing.py`. Tests: `tests/test_signing.py`.

## 1. The key

- On first login each install generates an **ECDSA P-256** key pair in the Android Keystore. The private key never leaves the device.
- Register the public key once with `POST /devices` as **base64 of the X.509 SubjectPublicKeyInfo DER**
  (what `publicKey.encoded` returns on Android). No PEM headers, no line breaks.
- Other curves (P-384, RSA) are refused.

## 2. The payload

Join these 9 fields with `|` (pipe), in this order, as UTF-8 text with no trailing newline:

| # | Field | Format |
|---|-------|--------|
| 1 | version | the literal `ibh-evidence-v1` |
| 2 | `file_sha256` | SHA-256 of the **exact file bytes you upload**, 64 lowercase hex characters |
| 3 | `captured_at` | the phone's clock at the shutter. UTC, ISO 8601, milliseconds, trailing `Z`: `2026-10-12T09:30:15.123Z` |
| 4 | `gps_time` | the GPS fix time at the shutter, same format: `2026-10-12T09:30:14.900Z` |
| 5 | `lat` | fixed 6 decimals: `6.459500` |
| 6 | `lon` | fixed 6 decimals: `7.500450` |
| 7 | `accuracy_m` | fixed 1 decimal: `8.5` |
| 8 | `project_id` | lowercase hyphenated UUID |
| 9 | `device_id` | the id used at registration (must not contain `\|` or line breaks) |

Rules:
- **Round lat, lon and accuracy yourself** (6, 6 and 1 decimals) before signing, and send those same rounded values to `POST /evidence`. The server formats what you send, so the strings match exactly.
- Compress the photo (about 1600 px, JPEG quality 80) **before** hashing and signing, so the signed file is exactly the uploaded file.
- `captured_at` and `gps_time` are read at the shutter and converted to UTC. Offline captures keep their original times. The server rejects the capture if they differ by more than 10 minutes.
- No `-0.000000`: write `0.000000`.

## 3. The signature

- Algorithm: **ECDSA with SHA-256** (Android `SHA256withECDSA`).
- Output: the **DER-encoded** signature (not raw r||s), sent as **base64**.

## 4. Test vector

Use it to check your Dart or Kotlin code builds the same payload.

```
file_sha256 = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
captured_at = 2026-10-12T09:30:15.123Z
gps_time = 2026-10-12T09:30:14.900Z
lat = 6.4595   lon = 7.50045   accuracy_m = 8.5
project_id = 11111111-2222-3333-4444-555555555555
device_id = device-abc
```

Payload:
```
ibh-evidence-v1|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|2026-10-12T09:30:15.123Z|2026-10-12T09:30:14.900Z|6.459500|7.500450|8.5|11111111-2222-3333-4444-555555555555|device-abc
```

Public key (base64):
```
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE9IrFmcVSdNmjuoJRI4im7R54NCLHk7pRij3SkCrTwKoqDb22YkZgbaF4ZkmK4/W5uMRNHzkzeu3GDGYynKPJEA==
```

A valid signature (base64) of that payload with that key. The server must accept it:
```
MEQCIBAxdJmFKYDGJpYNWPEQJy9B5PQAWMfH/ifm0uPsn4XHAiBLIQavipASpeM2WEH7BMlgYvtLtFQtYZ43t8oeGTovAg==
```

Your own signatures will differ every time, because ECDSA is randomised. Only the payload is deterministic.

## 5. What the server checks, in order

1. The file hash matches field 2.
2. The signature is valid for the registered, **non-revoked** device key.
3. The device belongs to the user, who is a party to the project.
4. The clock (`captured_at` within 10 minutes of `gps_time`, uploaded within 72 hours of capture), the geofence and the reuse checks.

A revoked key never verifies.
