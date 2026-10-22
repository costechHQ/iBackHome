"use client";

import { Images } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { toUiState } from "@/common/api/errors";
import { shortId, useEvidence, useMilestones, type EvidenceFilters } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDate, formatTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { EvidenceCard } from "@/common/ui/evidence";
import { SelectField } from "@/common/ui/field";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { EmptyState } from "@/common/ui/surfaces";

// WEB-CLIENT-010 Evidence gallery (read-only). Filters are the ones the API supports (milestone, captured by,
// type); the designed date range has no API filter yet and is left out. Clients never see rejected captures,
// and flagged ones read "Under review by iBackHome". Items are grouped by day in the client's time zone.

type By = "all" | "supervisor" | "contractor";
type Kind = "all" | "photo" | "video";

/** `initialMilestone`: open already filtered to one milestone (from "See the evidence"). */
export function EvidenceGallery({
  projectId,
  initialMilestone = "",
}: {
  projectId: string;
  initialMilestone?: string;
}) {
  const timeZone = useViewerTimeZone();
  const search = useSearchParams();
  const [milestoneId, setMilestoneId] = useState(initialMilestone);
  const [by, setBy] = useState<By>(search.get("by") === "contractor" ? "contractor" : "all");
  const [kind, setKind] = useState<Kind>("all");

  const milestones = useMilestones(projectId);
  const filters: EvidenceFilters = {
    ...(milestoneId ? { milestone_id: milestoneId } : {}),
    ...(by !== "all" ? { captured_by_role: by } : {}),
    ...(kind !== "all" ? { kind } : {}),
  };
  const evidence = useEvidence(projectId, filters);
  const visible = useMemo(
    () => (evidence.data ?? []).filter((e) => e.status !== "rejected"),
    [evidence.data],
  );

  const days = useMemo(() => {
    const groups = new Map<string, typeof visible>();
    for (const item of [...visible].sort((a, b) => b.captured_at.localeCompare(a.captured_at))) {
      const day = formatDate(item.captured_at, timeZone);
      groups.set(day, [...(groups.get(day) ?? []), item]);
    }
    return [...groups.entries()];
  }, [visible, timeZone]);

  const filtered = Boolean(milestoneId) || by !== "all" || kind !== "all";
  const clear = () => {
    setMilestoneId("");
    setBy("all");
    setKind("all");
  };
  const milestoneName = milestones.data?.find((m) => m.id === milestoneId)?.name;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 pb-24 sm:px-10">
      <h1 className="sr-only">Evidence</h1>
      <div className="flex flex-wrap items-end gap-4">
        <SelectField
          label="Milestone"
          className="w-full sm:w-60"
          value={milestoneId}
          onChange={(e) => setMilestoneId(e.target.value)}
        >
          <option value="">All milestones</option>
          {(milestones.data ?? []).map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </SelectField>
        <div className="flex flex-col gap-1.5">
          <span id="by-label" className="type-small font-semibold text-ink">
            Captured by
          </span>
          <SegmentedControl
            label="Captured by"
            value={by}
            onChange={setBy}
            segments={[
              { value: "all", label: "All" },
              { value: "supervisor", label: "Supervisor" },
              { value: "contractor", label: "Contractor" },
            ]}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="type-small font-semibold text-ink">Type</span>
          <SegmentedControl
            label="Type"
            value={kind}
            onChange={setKind}
            segments={[
              { value: "all", label: "All" },
              { value: "photo", label: "Photos" },
              { value: "video", label: "Videos" },
            ]}
          />
        </div>
        <p className="type-small ml-auto text-slate" aria-live="polite">
          <span className="font-semibold text-ink">{visible.length}</span>{" "}
          {visible.length === 1 ? "item" : "items"}
          {filtered ? (
            <>
              {" · "}
              <button type="button" className="font-semibold text-accent underline" onClick={clear}>
                Clear filters
              </button>
            </>
          ) : null}
        </p>
      </div>

      {evidence.isPending ? (
        <Loading label="Loading the evidence">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="aspect-video w-full" />
            ))}
          </div>
        </Loading>
      ) : evidence.error ? (
        <ServerErrorContent
          reference={(() => {
            const s = toUiState(evidence.error);
            return s.kind === "server" ? s.requestId : null;
          })()}
          onRetry={() => void evidence.refetch()}
        />
      ) : visible.length === 0 ? (
        <EmptyState
          icon={Images}
          title={milestoneName ? `Nothing for ${milestoneName} yet` : "No evidence yet"}
          action={
            filtered ? (
              <Button variant="secondary" onClick={clear}>
                Clear filters
              </Button>
            ) : null
          }
        >
          Evidence appears here as soon as it passes the checks.
        </EmptyState>
      ) : (
        days.map(([day, items]) => {
          const roles = new Set(items.map((i) => i.captured_by_role));
          const what =
            roles.size === 1 ? (roles.has("contractor") ? "contractor uploads" : "supervisor visit") : null;
          return (
            <section key={day} aria-label={day} className="flex flex-col gap-3">
              <h2 className="text-ink">
                <span className="font-semibold">{day}</span>
                {what ? <span className="text-slate"> · {what}</span> : null}
              </h2>
              <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {items.map((item) => (
                  <li key={item.id}>
                    <EvidenceCard
                      item={item}
                      audience="client"
                      reference={shortId(item.id)}
                      time={formatTime(item.captured_at, timeZone)}
                    />
                  </li>
                ))}
              </ul>
            </section>
          );
        })
      )}
    </div>
  );
}
