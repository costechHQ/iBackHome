// Where the dev seed driver runs: the local Docker Compose stack only (ENVIRONMENT=local), never staging or
// production. It calls the real API as the seeded people (backend/scripts/seed.py).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = fileURLToPath(new URL("../../..", import.meta.url));
export const STATE_DIR = fileURLToPath(new URL("../../.drive/", import.meta.url));
export const API = (process.env.IBH_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");
/** Storage as reachable from this machine; presigned URLs name the Docker host `storage:9000`. */
export const STORAGE = process.env.IBH_STORAGE ?? "127.0.0.1:9000";

/** A value from the repo's local .env (gitignored), where the webhook secrets live. */
export function localEnv(name: string): string {
  const fromProcess = process.env[name];
  if (fromProcess) return fromProcess;
  let text = "";
  try {
    text = readFileSync(`${REPO_ROOT}/.env`, "utf8");
  } catch {
    // no .env
  }
  const line = text.split(/\r?\n/).find((l) => l.startsWith(`${name}=`));
  const value = line?.slice(name.length + 1).trim();
  if (!value)
    throw new Error(`${name} is not set: add it to the repo's .env (see web/README.md, "Seed driver")`);
  return value;
}

export class DriveError extends Error {}
