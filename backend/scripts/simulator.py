"""Fill staging with realistic activity for the web phase, through the REST API. Owner: James.

Run from backend/ after scripts/seed.py (inside the api container on staging):

    uv run python scripts/simulator.py                        # in-process, against DATABASE_URL
    uv run python scripts/simulator.py --base-url http://localhost:8000 --photos 4
    uv run python scripts/simulator.py --photos-dir scripts/sim_photos   # real photos (sim_photos/fetch.sh)

For each seeded project, as the people seed.py created:
1. the contractor submits a bill of quantities; client, contractor and ops approve it -> project active;
2. the project's supervisor registers a phone key and uploads signed photo captures inside the
   geofence, exactly as the Flutter app will (features/evidence/SIGNING.md);
3. ops schedules an unannounced spot check by the other supervisor.
Every change goes through the API, so every rule, check and audit entry applies. The database is read
only to find the seeded people and sign them in (staging codes go by SMS, so OTP login can't be scripted).

Not simulated yet, and why (printed at the end):
- funding, claims, verify, approve: funding needs a Stripe test payment (decision pending), and
  verify/approve are Lilian's Day 3 (not on main);
- material orders: no route or service creates a supplier yet (Abigail).

Refuses to run when ENVIRONMENT=production.
"""

import argparse
import asyncio
import base64
import hashlib
import io
import random
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

import httpx  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.base.users import service as users  # noqa: E402
from app.base.users.models import User  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from scripts import seed  # noqa: E402

API = "/api/v1"
SIGNING_VERSION = "ibh-evidence-v1"

# A realistic three-stage BoQ (kobo). Quantities as strings: never floats near money.
BOQ = {
    "milestones": [
        {
            "name": "Foundation",
            "items": [
                {
                    "description": "Excavation of strip foundation",
                    "unit": "m3",
                    "quantity": "38",
                    "unit_price_minor": 450_000,
                },
                {
                    "description": "Concrete 1:2:4 for strip foundation",
                    "unit": "m3",
                    "quantity": "14.5",
                    "unit_price_minor": 9_500_000,
                },
                {
                    "description": "9-inch sandcrete blocks to DPC",
                    "unit": "nr",
                    "quantity": "1200",
                    "unit_price_minor": 65_000,
                },
            ],
        },
        {
            "name": "Blockwork to lintel",
            "items": [
                {
                    "description": "9-inch sandcrete blocks",
                    "unit": "nr",
                    "quantity": "4200",
                    "unit_price_minor": 65_000,
                },
                {
                    "description": "Cement (50 kg bags)",
                    "unit": "bag",
                    "quantity": "310",
                    "unit_price_minor": 980_000,
                },
                {
                    "description": "Lintel reinforcement (Y12)",
                    "unit": "length",
                    "quantity": "60",
                    "unit_price_minor": 1_150_000,
                },
            ],
        },
        {
            "name": "Roofing",
            "items": [
                {
                    "description": "Treated hardwood roof timber",
                    "unit": "nr",
                    "quantity": "180",
                    "unit_price_minor": 420_000,
                },
                {
                    "description": "Long-span aluminium roofing sheets",
                    "unit": "m2",
                    "quantity": "260",
                    "unit_price_minor": 1_250_000,
                },
            ],
        },
    ]
}


@dataclass
class Summary:
    done: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def print(self) -> None:
        for line in self.done:
            print(f"  [done]    {line}")
        for line in self.skipped:
            print(f"  [skipped] {line}")


class SimulatorError(RuntimeError):
    pass


class Api:
    """The iBackHome API, called as one person at a time."""

    def __init__(self, http: httpx.AsyncClient, run_id: str) -> None:
        self.http = http
        self.run_id = run_id
        self._n = 0

    async def call(
        self, method: str, path: str, as_user: User, json: Any = None, *, ok: tuple[int, ...] = (200, 201)
    ) -> Any:
        headers = {"Authorization": f"Bearer {users.create_access_token(as_user)}"}
        if method != "GET":
            self._n += 1
            headers["Idempotency-Key"] = f"sim-{self.run_id}-{self._n}"
        response = await self.http.request(method, API + path, json=json, headers=headers)
        if response.status_code not in ok:
            raise SimulatorError(f"{method} {path} -> {response.status_code}: {response.text[:300]}")
        return response.json() if response.content else None


# Signed captures (features/evidence/SIGNING.md)


def site_photo(rng: random.Random, width: int = 1280, height: int = 960) -> bytes:
    """A made-up site photo: sky, ground and random blockwork. Different every time, so the
    perceptual-hash reuse check never mistakes one simulated photo for another."""
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    horizon = rng.randint(height // 3, height // 2)
    for y in range(horizon):
        shade = 150 + int(90 * y / horizon)
        draw.line([(0, y), (width, y)], fill=(shade - 60, shade - 20, 255))
    draw.rectangle([0, horizon, width, height], fill=(rng.randint(120, 170), rng.randint(90, 120), 70))
    for _ in range(rng.randint(8, 16)):
        x, y = rng.randint(0, width - 200), rng.randint(horizon - 300, height - 120)
        w, h = rng.randint(60, 420), rng.randint(40, 300)
        grey = rng.randint(140, 220)
        draw.rectangle([x, y, x + w, y + h], fill=(grey, grey, grey - rng.randint(0, 30)))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=80)
    return out.getvalue()


def utc_ms(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def payload(
    sha256: str,
    captured_at: datetime,
    gps_time: datetime,
    lat: float,
    lon: float,
    accuracy_m: float,
    project_id: str,
    device_id: str,
) -> bytes:
    """The 9 fields joined with '|', exactly as SIGNING.md section 2 specifies."""
    fields = [
        SIGNING_VERSION,
        sha256,
        utc_ms(captured_at),
        utc_ms(gps_time),
        f"{lat:.6f}",
        f"{lon:.6f}",
        f"{accuracy_m:.1f}",
        project_id.lower(),
        device_id,
    ]
    return "|".join(fields).replace("-0.000000", "0.000000").encode("utf-8")


@dataclass
class Phone:
    """A supervisor's phone: an ECDSA P-256 key, like the Android Keystore one."""

    device_id: str
    key: ec.EllipticCurvePrivateKey = field(default_factory=lambda: ec.generate_private_key(ec.SECP256R1()))

    @property
    def public_key_b64(self) -> str:
        der = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(der).decode()

    def sign(self, data: bytes) -> str:
        return base64.b64encode(self.key.sign(data, ec.ECDSA(hashes.SHA256()))).decode()


async def capture(
    api: Api,
    storage: httpx.AsyncClient,
    supervisor: User,
    phone: Phone,
    project: dict[str, Any],
    rng: random.Random,
    now: datetime,
    photo: bytes | None = None,
) -> dict[str, Any]:
    """Take, upload and submit one signed photo from inside the project's geofence."""
    project_id = str(project["id"])
    pin = project["site"]["location"]
    photo = photo or site_photo(rng)
    sha256 = hashlib.sha256(photo).hexdigest()
    lat = round(float(pin["lat"]) + rng.uniform(-0.00005, 0.00005), 6)  # a few metres from the pin
    lon = round(float(pin["lon"]) + rng.uniform(-0.00005, 0.00005), 6)
    accuracy = round(rng.uniform(4, 12), 1)
    captured_at = now - timedelta(minutes=rng.randint(1, 30), milliseconds=rng.randint(0, 999))
    gps_time = captured_at - timedelta(milliseconds=rng.randint(100, 900))

    slot = await api.call(
        "POST",
        "/evidence/upload-url",
        supervisor,
        {"project_id": project_id, "kind": "photo", "content_type": "image/jpeg"},
    )
    upload = await storage.request(
        slot.get("method", "PUT"), slot["upload_url"], content=photo, headers=slot.get("headers") or {}
    )
    if upload.status_code >= 300:
        raise SimulatorError(f"upload to storage -> {upload.status_code}")

    signed = payload(sha256, captured_at, gps_time, lat, lon, accuracy, project_id, phone.device_id)
    body = {
        "project_id": project_id,
        "kind": "photo",
        "storage_key": slot["storage_key"],
        "file_sha256": sha256,
        "captured_at": captured_at.isoformat(),
        "gps_time": gps_time.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "accuracy_m": accuracy,
        "device_id": phone.device_id,
        "signature": phone.sign(signed),
    }
    result: dict[str, Any] = await api.call("POST", "/evidence", supervisor, body)
    return result


# The run


async def find_project(api: Api, client: User, title: str) -> dict[str, Any]:
    page = await api.call("GET", "/projects?limit=100", client)
    match = next((p for p in page["items"] if p["title"] == title), None)
    if match is None:
        raise SimulatorError(f"project {title!r} not found: run scripts/seed.py first")
    detail: dict[str, Any] = await api.call("GET", f"/projects/{match['id']}", client)
    return detail


async def activate(api: Api, project: dict[str, Any], people: dict[str, User], summary: Summary) -> None:
    """Submit and approve the BoQ (three approvals) unless the project is already past that."""
    pid, title = project["id"], project["title"]
    if project["status"] not in ("draft", "boq_review"):
        summary.skipped.append(f"{title}: BoQ already approved (status {project['status']})")
        return
    await api.call("PUT", f"/projects/{pid}/boq", people["contractor"], BOQ)
    for who in ("client", "contractor", "ops"):
        await api.call("POST", f"/projects/{pid}/boq/approve", people[who])
    summary.done.append(f"{title}: BoQ submitted and approved by client, contractor and ops -> active")


async def simulate(
    http: httpx.AsyncClient,
    storage: httpx.AsyncClient,
    people: dict[str, User],
    *,
    photos: int = 3,
    library: list[bytes] | None = None,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> Summary:
    """Run the simulation as `people` (seed.py's keys). Returns what was done and skipped."""
    now = now or datetime.now(UTC)
    rng = rng or random.Random()  # noqa: S311 - draws fake photos and GPS jitter, not secrets
    run_id = uuid.uuid4().hex[:8]
    api = Api(http, run_id)
    summary = Summary()

    for project_seed in seed.PROJECTS:
        project = await find_project(api, people["client"], project_seed.title)
        await activate(api, project, people, summary)

        supervisor = people[project_seed.supervisor]
        phone = Phone(device_id=f"sim-{project_seed.supervisor}-{run_id}")
        await api.call(
            "POST", "/devices", supervisor, {"device_id": phone.device_id, "public_key": phone.public_key_b64}
        )
        for _ in range(photos):
            real = library.pop() if library else None  # each real photo is used once per run
            await capture(api, storage, supervisor, phone, project, rng, now, real)
        summary.done.append(
            f"{project['title']}: {photos} signed photos by {supervisor.full_name} (checks queued)"
        )

        visitor_key = "supervisor_2" if project_seed.supervisor == "supervisor" else "supervisor"
        tomorrow_10am_lagos = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        await api.call(
            "POST",
            f"/projects/{project['id']}/spot-checks",
            people["ops"],
            {"supervisor_id": str(people[visitor_key].id), "scheduled_for": tomorrow_10am_lagos.isoformat()},
        )
        summary.done.append(
            f"{project['title']}: spot check by {people[visitor_key].full_name} tomorrow 10:00 WAT"
        )

    summary.skipped += [
        "funding, claims, verification and approval: funding needs a Stripe test payment (decision pending); "
        "verify and approve are Lilian's Day 3",
        "material orders: no route or service creates a supplier yet (Abigail)",
    ]
    return summary


def refuse_production() -> None:
    if get_settings().environment == "production":
        raise SystemExit("simulator.py refuses to run with ENVIRONMENT=production: it creates test activity.")


async def load_people() -> dict[str, User]:
    """The seeded people, read only to sign them in (see the module docstring)."""
    async with SessionLocal() as session:
        people: dict[str, User] = {}
        for person in seed.USERS:
            match = User.phone == person.phone if person.phone else User.email == person.email
            user = await session.scalar(select(User).where(match))
            if user is None:
                raise SystemExit(f"{person.full_name} isn't in the database: run scripts/seed.py first")
            people[person.key] = user
        return people


def load_library(photos_dir: Path, needed: int) -> list[bytes]:
    """Real JPEGs from `photos_dir`, shuffled. Every capture needs its own, or the reuse check flags it."""
    files = sorted(photos_dir.glob("*.jpg"))
    if len(files) < needed:
        sys.exit(f"{photos_dir} has {len(files)} .jpg files, {needed} needed (run sim_photos/fetch.sh)")
    random.shuffle(files)  # noqa: S311 - picks which photo goes where, not a secret
    return [path.read_bytes() for path in files]


async def main(base_url: str | None, photos: int, photos_dir: Path | None) -> None:
    refuse_production()
    library = load_library(photos_dir, photos * len(seed.PROJECTS)) if photos_dir else None
    people = await load_people()
    if base_url:
        http = httpx.AsyncClient(base_url=base_url, timeout=30)
    else:
        from app.main import app

        http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://simulator", timeout=30
        )
    async with http, httpx.AsyncClient(timeout=30) as storage:
        summary = await simulate(http, storage, people, photos=photos, library=library)
    print("Simulation finished:")
    summary.print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", help="a running API, e.g. http://localhost:8000 (default: in-process)")
    parser.add_argument("--photos", type=int, default=3, help="signed photos per project (default 3)")
    parser.add_argument(
        "--photos-dir", type=Path, help="use real .jpg files from this folder instead of drawn ones"
    )
    args = parser.parse_args()
    if sys.platform == "win32":  # async psycopg can't use Windows' default event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.base_url, args.photos, args.photos_dir))
