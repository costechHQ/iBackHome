// Signing in as the seeded people. Locally (ENVIRONMENT=local) the API writes each login code to its log, so
// the driver reads it from `docker compose logs api`. Tokens are kept in web/.drive/ (gitignored) and refreshed,
// because the backend allows only 3 codes per phone or email per 15 minutes.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";

import createClient from "openapi-fetch";

import type { paths } from "../../src/common/api/schema";
import { API, DriveError, REPO_ROOT, STATE_DIR } from "./env";

export type Person = { key: string; identifier: string; channel: "sms" | "email" };

// backend/scripts/seed.py
export const PEOPLE = {
  client: { key: "client", identifier: "adaeze.client@example.com", channel: "email" },
  contractor: { key: "contractor", identifier: "+2348030000001", channel: "sms" },
  supervisor: { key: "supervisor", identifier: "+2348030000002", channel: "sms" },
  supervisor_2: { key: "supervisor_2", identifier: "+2348030000005", channel: "sms" },
  ops: { key: "ops", identifier: "+2348030000004", channel: "sms" },
} as const satisfies Record<string, Person>;

type Tokens = { access_token: string; refresh_token: string; expires_at: number };
const TOKENS = `${STATE_DIR}tokens.json`;

function load(): Record<string, Tokens> {
  try {
    return JSON.parse(readFileSync(TOKENS, "utf8")) as Record<string, Tokens>;
  } catch {
    return {};
  }
}

function save(all: Record<string, Tokens>) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(TOKENS, JSON.stringify(all, null, 2));
}

const raw = createClient<paths>({ baseUrl: API });

function latestCode(identifier: string): string | null {
  const logs = execFileSync("docker", ["compose", "logs", "api", "--since", "3m"], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const escaped = identifier.replace(/[.+]/g, "\\$&");
  const matches = [...logs.matchAll(new RegExp(`to ${escaped}: Your iBackHome code is (\\d{6})`, "g"))];
  return matches.at(-1)?.[1] ?? null;
}

async function freshTokens(person: Person): Promise<Tokens> {
  const request = await raw.POST("/api/v1/auth/otp/request", {
    body: { identifier: person.identifier, channel: person.channel },
    headers: { "Idempotency-Key": randomUUID() },
  });
  if (!request.response.ok) {
    throw new DriveError(
      `login code for ${person.key}: HTTP ${request.response.status} ${JSON.stringify(request.error)}`,
    );
  }
  let code: string | null = null;
  for (let i = 0; i < 10 && !code; i++) {
    code = latestCode(person.identifier);
    if (!code) await new Promise((r) => setTimeout(r, 500));
  }
  if (!code)
    throw new DriveError(`no login code for ${person.identifier} in the api log (is ENVIRONMENT=local?)`);
  const verify = await raw.POST("/api/v1/auth/otp/verify", { body: { identifier: person.identifier, code } });
  if (!verify.data) throw new DriveError(`sign-in for ${person.key}: HTTP ${verify.response.status}`);
  return { ...verify.data, expires_at: Date.now() + verify.data.expires_in * 1000 };
}

/** A bearer token for `person`: cached, refreshed, or a new sign-in. */
export async function tokenFor(person: Person): Promise<string> {
  const all = load();
  let tokens = all[person.key];
  if (tokens && tokens.expires_at - 60_000 > Date.now()) return tokens.access_token;
  if (tokens) {
    const refreshed = await raw.POST("/api/v1/auth/refresh", {
      body: { refresh_token: tokens.refresh_token },
    });
    tokens = refreshed.data
      ? { ...refreshed.data, expires_at: Date.now() + refreshed.data.expires_in * 1000 }
      : undefined;
  }
  tokens ??= await freshTokens(person);
  all[person.key] = tokens;
  save(all);
  return tokens.access_token;
}

/** The generated API client, signed in as `person`. */
export async function apiAs(person: Person) {
  const token = await tokenFor(person);
  return createClient<paths>({ baseUrl: API, headers: { authorization: `Bearer ${token}` } });
}

/** Unwraps an openapi-fetch result or stops the run with the backend's error. */
export function ok<T>(what: string, result: { data?: T; error?: unknown; response: Response }): T {
  if (!result.response.ok || result.data === undefined) {
    throw new DriveError(`${what}: HTTP ${result.response.status} ${JSON.stringify(result.error)}`);
  }
  return result.data;
}
