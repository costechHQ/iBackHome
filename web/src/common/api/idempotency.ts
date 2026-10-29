// One Idempotency-Key per write action, reused for that action's retries (Docs/api-guide.md: "the same key
// when you retry that action"). A retry with the same input returns the first answer instead of doing the work
// twice. Changing the input makes it a new action with a new key (the backend refuses a key reused for
// different input). After a success the next submit is a new action.

/**
 * A random UUID. `crypto.randomUUID` exists only in secure contexts (HTTPS or localhost), so on a phone opening
 * the dev server at http://192.168.x.x:3000 it is undefined and every write failed with a generic error before
 * reaching the API. `getRandomValues` works everywhere.
 */
export function randomKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6]! & 0x0f) | 0x40;
  b[8] = (b[8]! & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export class IdempotentAction<Input> {
  private key: string | null = null;
  private input: string | null = null;

  constructor(private readonly newKey: () => string = randomKey) {}

  /** The key to send for this input. */
  keyFor(input: Input): string {
    const serialised = JSON.stringify(input ?? null);
    if (this.key === null || serialised !== this.input) {
      this.key = this.newKey();
      this.input = serialised;
    }
    return this.key;
  }

  /** Call after the server accepted the write: the next submit starts a new action. */
  done(): void {
    this.key = null;
    this.input = null;
  }
}
