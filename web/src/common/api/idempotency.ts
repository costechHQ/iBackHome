// One Idempotency-Key per write action, reused for that action's retries (Docs/api-guide.md: "the same key
// when you retry that action"). A retry with the same input returns the first answer instead of doing the work
// twice. Changing the input makes it a new action with a new key (the backend refuses a key reused for
// different input). After a success the next submit is a new action.

export class IdempotentAction<Input> {
  private key: string | null = null;
  private input: string | null = null;

  constructor(private readonly newKey: () => string = () => crypto.randomUUID()) {}

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
