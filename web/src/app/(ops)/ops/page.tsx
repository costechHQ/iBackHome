import { SignOutButton } from "@/common/auth/sign-out-button";

// W1a placeholder: proves sign-in lands on the right portal. Replaced by the designed ops home in W2/W3.
export default function OpsHome() {
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 px-4 py-16">
      <h1 className="type-h2 text-ink">Signed in</h1>
      <SignOutButton className="self-start text-accent underline hover:text-accent-hover" />
    </main>
  );
}
