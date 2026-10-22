"use client";

import Link from "next/link";

import { ConflictState } from "@/common/layout/system-pages";
import { Button } from "@/common/ui/button";

// A 409 on approve or dispute means the milestone moved on before this request landed (approved on another
// device, already disputed, sent back). WEB-CLIENT-024 "409": say what happened and that nothing was done twice.

export function conflictCopy(name: string, status: string): { title: string; body: string } {
  switch (status) {
    case "approved":
    case "released":
      return {
        title: `${name} was already approved`,
        body: "You approved it on another device or tab, so nothing was sent twice. The release is in progress.",
      };
    case "disputed":
      return {
        title: `${name} is under dispute`,
        body: "A dispute pauses the release, so nothing was released or approved. Our team is reviewing it.",
      };
    default:
      return {
        title: `${name} changed while you were deciding`,
        body: "It isn't waiting for your approval any more, so nothing was sent. Check where it is now.",
      };
  }
}

export function MilestoneConflict({ name, status, href }: { name: string; status: string; href: string }) {
  const copy = conflictCopy(name, status);
  return (
    <ConflictState
      title={copy.title}
      code="Error 409 · nothing was sent twice"
      actions={
        <Button asChild size="lg">
          <Link href={href}>See where {name} is</Link>
        </Button>
      }
    >
      <p>{copy.body}</p>
    </ConflictState>
  );
}
