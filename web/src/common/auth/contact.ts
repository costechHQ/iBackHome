// Where a code goes when someone signs back in after their session ended: their email, else their phone.
// A plain module so the portal layouts (server) can use it.

export type Contact = { identifier: string; channel: "email" | "sms" };

export function contactOf(me: { email?: string | null; phone?: string | null }): Contact | null {
  if (me.email) return { identifier: me.email, channel: "email" };
  if (me.phone) return { identifier: me.phone, channel: "sms" };
  return null;
}
