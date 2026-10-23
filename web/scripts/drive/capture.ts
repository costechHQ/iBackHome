// A supervisor's phone, as backend/app/features/evidence/SIGNING.md describes it: an ECDSA P-256 key
// (Android Keystore stand-in), a 9-field payload signed with SHA256withECDSA (DER, base64), the photo uploaded to
// the presigned URL, then POST /evidence with the milestone, so the capture counts toward verification.
import { execFileSync } from "node:child_process";
import {
  createHash,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  randomUUID,
  sign,
} from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { request } from "node:http";

import type { Person } from "./session";
import { apiAs, ok } from "./session";
import { DriveError, REPO_ROOT, STATE_DIR, STORAGE } from "./env";

const VERSION = "ibh-evidence-v1";

type Device = { device_id: string; private_key_pem: string };

function devicePath(person: Person) {
  return `${STATE_DIR}device-${person.key}.json`;
}

/** The person's phone key, registered once with POST /devices and kept in web/.drive/. */
async function phone(person: Person): Promise<Device> {
  try {
    return JSON.parse(readFileSync(devicePath(person), "utf8")) as Device;
  } catch {
    // first run: make and register a key
  }
  const { privateKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
  const device: Device = {
    device_id: `drive-${person.key}-${randomUUID().slice(0, 8)}`,
    private_key_pem: privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
  };
  const publicKey = createPublicKey(createPrivateKey(device.private_key_pem))
    .export({ type: "spki", format: "der" })
    .toString("base64");
  const api = await apiAs(person);
  ok(
    "register device",
    await api.POST("/api/v1/devices", {
      body: { device_id: device.device_id, public_key: publicKey },
      headers: { "Idempotency-Key": randomUUID() },
    }),
  );
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(devicePath(person), JSON.stringify(device, null, 2));
  return device;
}

const utcMs = (d: Date) => d.toISOString(); // already "YYYY-MM-DDTHH:mm:ss.sssZ"
const fixed = (n: number, digits: number) => n.toFixed(digits).replace(/^-0\.0+$/, (z) => z.slice(1));

/** A made-up site photo, different every time (simulator.site_photo), made by Pillow in the api container. */
export function sitePhoto(): Buffer {
  const code =
    "import base64,random,sys; sys.path.insert(0,'scripts'); import simulator; " +
    "sys.stdout.write(base64.b64encode(simulator.site_photo(random.Random())).decode())";
  const out = execFileSync("docker", ["compose", "exec", "-T", "api", "python", "-c", code], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  return Buffer.from(out.trim().split(/\s+/).at(-1) ?? "", "base64");
}

/** PUT to the presigned URL. It names the Docker host storage:9000, which is signed, so connect to
 *  127.0.0.1:9000 and keep the Host header. */
function upload(url: string, body: Buffer, headers: Record<string, string>): Promise<number> {
  const target = new URL(url);
  const [hostname, port] = STORAGE.split(":");
  return new Promise((resolve, reject) => {
    const req = request(
      {
        hostname,
        port: Number(port ?? 80),
        method: "PUT",
        path: `${target.pathname}${target.search}`,
        headers: { ...headers, host: target.host, "content-length": body.length },
      },
      (res) => {
        res.resume();
        res.on("end", () => resolve(res.statusCode ?? 0));
      },
    );
    req.on("error", reject);
    req.end(body);
  });
}

export async function capture(
  person: Person,
  project: { id: string; site: { location: { lat: number; lon: number } } | null },
  milestoneId: string,
  photo: Buffer = sitePhoto(),
): Promise<string> {
  if (!project.site) throw new DriveError("the project has no site");
  const device = await phone(person);
  const api = await apiAs(person);
  const sha256 = createHash("sha256").update(photo).digest("hex");
  const lat = Number(fixed(project.site.location.lat + (Math.random() - 0.5) * 0.0001, 6));
  const lon = Number(fixed(project.site.location.lon + (Math.random() - 0.5) * 0.0001, 6));
  const accuracy = Number(fixed(4 + Math.random() * 8, 1));
  const capturedAt = new Date(Date.now() - 60_000);
  const gpsTime = new Date(capturedAt.getTime() - 400);

  const slot = ok(
    "upload slot",
    await api.POST("/api/v1/evidence/upload-url", {
      body: { project_id: project.id, kind: "photo", content_type: "image/jpeg" },
      headers: { "Idempotency-Key": randomUUID() },
    }),
  );
  const status = await upload(slot.upload_url, photo, (slot.headers ?? {}) as Record<string, string>);
  if (status >= 300) throw new DriveError(`upload to storage: HTTP ${status}`);

  const payload = [
    VERSION,
    sha256,
    utcMs(capturedAt),
    utcMs(gpsTime),
    fixed(lat, 6),
    fixed(lon, 6),
    fixed(accuracy, 1),
    project.id.toLowerCase(),
    device.device_id,
  ].join("|");
  const signature = sign(
    "sha256",
    Buffer.from(payload, "utf8"),
    createPrivateKey(device.private_key_pem),
  ).toString("base64");

  const evidence = ok(
    "submit evidence",
    await api.POST("/api/v1/evidence", {
      body: {
        project_id: project.id,
        kind: "photo",
        storage_key: slot.storage_key,
        file_sha256: sha256,
        captured_at: capturedAt.toISOString(),
        gps_time: gpsTime.toISOString(),
        latitude: lat,
        longitude: lon,
        accuracy_m: accuracy,
        device_id: device.device_id,
        signature,
        milestone_id: milestoneId,
      },
      headers: { "Idempotency-Key": randomUUID() },
    }),
  );
  return evidence.id;
}

/** Waits for the worker's checks (evidence.run_checks) to accept the captures. */
/** Waits until the worker has checked one capture, and returns its status (accepted, flagged or rejected). */
export async function waitChecked(person: Person, projectId: string, id: string, timeoutMs = 60_000) {
  const api = await apiAs(person);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const page = ok(
      "gallery",
      await api.GET("/api/v1/projects/{project_id}/evidence", {
        params: { path: { project_id: projectId }, query: { limit: 200 } },
      }),
    );
    const status = page.items.find((e) => e.id === id)?.status;
    if (status && status !== "pending_checks") return status;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new DriveError("the evidence checks didn't finish in time (is the worker running?)");
}

export async function waitAccepted(person: Person, projectId: string, ids: string[], timeoutMs = 60_000) {
  const api = await apiAs(person);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const page = ok(
      "gallery",
      await api.GET("/api/v1/projects/{project_id}/evidence", {
        params: { path: { project_id: projectId }, query: { limit: 200 } },
      }),
    );
    const mine = page.items.filter((e) => ids.includes(e.id));
    const bad = mine.find((e) => e.status === "rejected" || e.status === "flagged");
    if (bad) throw new DriveError(`capture ${bad.id} was ${bad.status}: ${bad.reject_reason ?? ""}`);
    if (mine.length === ids.length && mine.every((e) => e.status === "accepted")) return;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new DriveError("the evidence checks didn't finish in time (is the worker running?)");
}
