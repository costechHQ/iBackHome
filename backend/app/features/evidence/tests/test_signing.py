import base64
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.core.errors import AppError
from app.features.evidence.signing import canonical_payload, verify_signature

SHA = "a" * 64
WHEN = datetime(2026, 10, 12, 9, 30, 15, 123000, tzinfo=UTC)
GPS = datetime(2026, 10, 12, 9, 30, 14, 900000, tzinfo=UTC)
PROJECT = "11111111-2222-3333-4444-555555555555"

# Fixed test vector, also published in SIGNING.md so the Flutter side can check its own code.
VECTOR_PAYLOAD = (
    b"ibh-evidence-v1|"
    + SHA.encode()
    + b"|2026-10-12T09:30:15.123Z|2026-10-12T09:30:14.900Z|6.459500|7.500450|8.5|"
    + PROJECT.encode()
    + b"|device-abc"
)
VECTOR_PUBLIC_KEY = (
    "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE9IrFmcVSdNmjuoJRI4im7R54NCLHk7pRij"
    "3SkCrTwKoqDb22YkZgbaF4ZkmK4/W5uMRNHzkzeu3GDGYynKPJEA=="
)
VECTOR_SIGNATURE = (
    "MEQCIBAxdJmFKYDGJpYNWPEQJy9B5PQAWMfH/ifm0uPsn4XHAiBLIQavipASpeM2WEH7BMlgYvtLtFQtYZ43t8oeGTovAg=="
)


def payload(**overrides: object) -> bytes:
    args: dict[str, object] = {
        "file_sha256": SHA,
        "captured_at": WHEN,
        "gps_time": GPS,
        "lat": 6.4595,
        "lon": 7.50045,
        "accuracy_m": 8.5,
        "project_id": PROJECT,
        "device_id": "device-abc",
    }
    args.update(overrides)
    return canonical_payload(**args)  # type: ignore[arg-type]


def make_key() -> tuple[ec.EllipticCurvePrivateKey, str]:
    private = ec.generate_private_key(ec.SECP256R1())
    der = private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private, base64.b64encode(der).decode()


def sign(private: ec.EllipticCurvePrivateKey, data: bytes) -> str:
    return base64.b64encode(private.sign(data, ec.ECDSA(hashes.SHA256()))).decode()


# canonical_payload


def test_payload_matches_documented_vector() -> None:
    assert payload() == VECTOR_PAYLOAD


def test_payload_is_deterministic_and_field_order_is_fixed() -> None:
    assert payload() == payload()
    assert payload().decode().split("|")[0] == "ibh-evidence-v1"
    assert len(payload().decode().split("|")) == 9


@pytest.mark.parametrize(
    "change",
    [
        {"file_sha256": "b" * 64},
        {"captured_at": WHEN + timedelta(milliseconds=1)},
        {"gps_time": GPS + timedelta(milliseconds=1)},
        {"lat": 6.4596},
        {"lon": 7.50046},
        {"accuracy_m": 8.6},
        {"project_id": "11111111-2222-3333-4444-555555555556"},
        {"device_id": "device-abd"},
    ],
)
def test_changing_any_field_changes_the_payload(change: dict[str, object]) -> None:
    assert payload(**change) != payload()


def test_other_timezones_are_converted_to_utc() -> None:
    lagos = timezone(timedelta(hours=1))
    assert payload(captured_at=WHEN.astimezone(lagos)) == payload()


def test_uuid_object_and_uppercase_string_are_normalised() -> None:
    assert payload(project_id=uuid.UUID(PROJECT)) == payload()
    assert payload(project_id=PROJECT.upper()) == payload()


def test_negative_zero_is_not_signed_as_minus_zero() -> None:
    assert b"|0.000000|" in payload(lat=-0.0000001)


@pytest.mark.parametrize(
    "bad",
    [
        {"file_sha256": "A" * 64},
        {"file_sha256": "abc"},
        {"captured_at": datetime(2026, 10, 12, 9, 30)},
        {"gps_time": datetime(2026, 10, 12, 9, 30)},
        {"lat": 91.0},
        {"lon": -181.0},
        {"accuracy_m": -1.0},
        {"project_id": "not-a-uuid"},
        {"device_id": ""},
        {"device_id": "a|b"},
    ],
)
def test_invalid_metadata_is_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(AppError) as err:
        payload(**bad)
    assert err.value.code == "invalid_capture_metadata"
    assert err.value.status_code == 422


# verify_signature


def test_valid_signature_passes() -> None:
    private, public = make_key()
    assert verify_signature(public, payload(), sign(private, payload())) is True


def test_documented_vector_verifies() -> None:
    assert verify_signature(VECTOR_PUBLIC_KEY, VECTOR_PAYLOAD, VECTOR_SIGNATURE) is True


def test_one_changed_byte_in_payload_fails() -> None:
    private, public = make_key()
    signature = sign(private, payload())
    tampered = bytearray(payload())
    tampered[-1] ^= 0x01
    assert verify_signature(public, bytes(tampered), signature) is False


def test_signature_from_a_different_key_fails() -> None:
    private, _ = make_key()
    _, other_public = make_key()
    assert verify_signature(other_public, payload(), sign(private, payload())) is False


def test_one_changed_byte_in_signature_fails() -> None:
    private, public = make_key()
    raw = bytearray(base64.b64decode(sign(private, payload())))
    raw[-1] ^= 0x01
    assert verify_signature(public, payload(), base64.b64encode(bytes(raw)).decode()) is False


def test_revoked_key_fails_even_with_a_valid_signature() -> None:
    private, public = make_key()
    signature = sign(private, payload())
    assert verify_signature(public, payload(), signature, revoked_at=None) is True
    assert verify_signature(public, payload(), signature, revoked_at=datetime.now(UTC)) is False


def test_malformed_input_returns_false_instead_of_raising() -> None:
    private, public = make_key()
    signature = sign(private, payload())
    assert verify_signature("not base64!", payload(), signature) is False
    assert verify_signature(public, payload(), "not base64!") is False
    assert verify_signature(base64.b64encode(b"junk").decode(), payload(), signature) is False
    assert verify_signature(public, payload(), "") is False


def test_non_p256_keys_are_refused() -> None:
    p384 = ec.generate_private_key(ec.SECP384R1())
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for key in (p384, rsa_key):
        der = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public = base64.b64encode(der).decode()
        assert verify_signature(public, payload(), sign(p384, payload())) is False
