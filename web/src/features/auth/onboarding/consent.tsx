"use client";

import { useQuery } from "@tanstack/react-query";
import { Lock, MapPin, Phone, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { useWrite } from "@/common/api/use-write";
import { signOutHere } from "@/common/auth/leave";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";

// "Your data, your consent" (WEB-PUBLIC-010 card 10, NDPA 2023), before a client or contractor uses their
// portal. It records agreement to the current terms of use and privacy policy versions (GET/POST /me/consent).
// The documents themselves aren't published yet, so the boxes name them without links (PACKAGE-REPORT W-27).

const USES = [
  { icon: Phone, title: "Contact details", text: "to sign you in and send updates" },
  { icon: MapPin, title: "Site photos and locations", text: "to prove work happened on your site" },
  { icon: Lock, title: "Payment records", text: "shared with the licensed escrow partner and Stripe" },
  {
    icon: ShieldCheck,
    title: "Only what’s needed",
    text: "access is logged, and you can ask to see or delete it",
  },
];

export function ConsentCard({ onDone }: { onDone: () => void }) {
  const ids = { terms: useId(), privacy: useId() };
  const [terms, setTerms] = useState(false);
  const [privacy, setPrivacy] = useState(false);
  const versions = useQuery({
    queryKey: ["me", "consent"],
    queryFn: () => call(api().GET("/api/v1/me/consent")),
  });
  const agree = useWrite(
    (input: { terms_version: string; privacy_version: string }, key: string) =>
      call(api().POST("/api/v1/me/consent", { body: input, headers: { "Idempotency-Key": key } })),
    {
      onSuccess: onDone,
      onError: (error) => {
        // The documents changed while the card was open: show the current ones before agreeing again.
        if (error instanceof ApiError && error.code === "consent_version_outdated") {
          setTerms(false);
          setPrivacy(false);
          void versions.refetch();
        }
      },
    },
  );
  const outdated = agree.error instanceof ApiError && agree.error.code === "consent_version_outdated";

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <p className="type-caption text-muted uppercase">New account · one last step</p>
        <h1 className="type-h1 text-ink">Your data, your consent</h1>
        <p className="text-slate">
          Under the Nigeria Data Protection Act 2023 we need your agreement before we create your account.
        </p>
      </div>
      <div className="flex flex-col gap-3 rounded-card bg-mist p-4">
        <p className="type-small font-semibold text-ink">What we use, and why</p>
        <ul className="flex flex-col gap-3">
          {USES.map(({ icon: Icon, title, text }) => (
            <li key={title} className="type-small flex items-start gap-3 text-slate">
              <Icon aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none text-ink" />
              <span>
                <span className="font-semibold text-ink">{title}</span> — {text}
              </span>
            </li>
          ))}
        </ul>
      </div>
      {outdated ? (
        <Alert tone="warn" title="The terms or privacy policy just changed">
          Read the current versions and agree again.
        </Alert>
      ) : agree.error ? (
        <Alert tone="bad" title="We couldn’t save your agreement">
          Nothing was saved. Try again.
        </Alert>
      ) : null}
      <div className="flex flex-col gap-3">
        <label htmlFor={ids.terms} className="flex items-start gap-3 text-ink">
          <input
            id={ids.terms}
            type="checkbox"
            checked={terms}
            onChange={(e) => setTerms(e.target.checked)}
            className="mt-1 size-5 flex-none"
          />
          <span>
            I agree to the{" "}
            <Link href="/terms" target="_blank" className="text-accent underline">
              Terms of use
            </Link>
            {versions.data ? ` (version ${versions.data.terms_version})` : ""}.{" "}
            <span className="text-muted">Required</span>
          </span>
        </label>
        <label htmlFor={ids.privacy} className="flex items-start gap-3 text-ink">
          <input
            id={ids.privacy}
            type="checkbox"
            checked={privacy}
            onChange={(e) => setPrivacy(e.target.checked)}
            className="mt-1 size-5 flex-none"
          />
          <span>
            I consent to iBackHome processing my personal data — including site photos, locations and payment
            records — to run my projects, as described in the{" "}
            <Link href="/privacy" target="_blank" className="text-accent underline">
              Privacy policy
            </Link>
            {versions.data ? ` (version ${versions.data.privacy_version})` : ""}.{" "}
            <span className="text-muted">Required</span>
          </span>
        </label>
      </div>
      <Button
        size="lg"
        block
        loading={agree.isPending}
        disabled={!terms || !privacy || !versions.data}
        onClick={() =>
          versions.data &&
          agree.mutate({
            terms_version: versions.data.terms_version,
            privacy_version: versions.data.privacy_version,
          })
        }
      >
        Agree and continue
      </Button>
      <p className="type-small text-slate">
        Both boxes are needed to continue. You can withdraw consent later by contacting us.
      </p>
      <button
        type="button"
        onClick={() => void signOutHere()}
        className="self-start rounded-control font-semibold text-accent underline"
      >
        Don&apos;t agree — sign out
      </button>
    </div>
  );
}
