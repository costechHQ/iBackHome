// Shared by the server redirect (projects/[id]) and client screens, so not in a "use client" module.

/** The milestone the Milestones tab opens: the one waiting for the client, else the work in progress. */
export function milestoneNeedingAttention(
  milestones: readonly { id: string; status: string; sequence: number }[],
) {
  const ordered = [...milestones].sort((a, b) => a.sequence - b.sequence);
  return (
    ordered.find((m) => m.status === "verified") ??
    ordered.find((m) => m.status === "disputed" || m.status === "approved") ??
    ordered.find((m) => m.status === "claimed") ??
    ordered.find((m) => m.status !== "released") ??
    ordered.at(-1)
  );
}
