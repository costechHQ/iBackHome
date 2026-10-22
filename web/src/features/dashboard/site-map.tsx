"use client";

import dynamic from "next/dynamic";
import { useId, useState } from "react";

import { shortId, useEvidence, useMilestones, useProject, type Milestone } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { fromGeoJson, insidePolygon } from "@/common/map/geo";
import { formatDateTime } from "@/common/time";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

// WEB-CLIENT-012 Project site map at /projects/:id/site-map: the boundary and its 25 m tolerance, the site
// pin, and where each piece of evidence was captured, filtered by milestone and by who captured it. Rejected
// captures never appear for the client. Each capture is also listed in words (the map is never the only way
// to read it). "Open evidence" goes to the gallery: evidence detail needs MX-07.

const GeofenceMap = dynamic(() => import("@/common/map/geofence-map").then((m) => m.GeofenceMap), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

type Show = { supervisor: boolean; contractor: boolean; review: boolean };

export function SiteMap({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const ids = { milestone: useId() };
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const [milestoneId, setMilestoneId] = useState("");
  const [show, setShow] = useState<Show>({ supervisor: true, contractor: true, review: true });
  const evidence = useEvidence(projectId, milestoneId ? { milestone_id: milestoneId } : {});

  if (project.isPending || milestones.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the site map">
          <Skeleton className="h-96 w-full" />
        </Loading>
      </div>
    );
  if (!project.data) return <ServerErrorContent reference={null} onRetry={() => void project.refetch()} />;

  const p = project.data;
  const corners = p.site ? fromGeoJson(p.site.geofence) : [];
  const pin = p.site ? { lat: p.site.location.lat, lon: p.site.location.lon } : null;
  const all = (evidence.data ?? []).filter(
    (e) => e.status !== "rejected" && e.latitude != null && e.longitude != null,
  );
  const counts = {
    supervisor: all.filter((e) => e.captured_by_role === "supervisor" && e.status !== "flagged").length,
    contractor: all.filter((e) => e.captured_by_role === "contractor").length,
    review: all.filter((e) => e.status === "flagged").length,
  };
  const visible = all.filter((e) =>
    e.status === "flagged"
      ? show.review
      : e.captured_by_role === "contractor"
        ? show.contractor
        : show.supervisor,
  );
  const ms = [...((milestones.data ?? []) as Milestone[])].sort((a, b) => a.sequence - b.sequence);

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <h2 className="sr-only">Site map</h2>
      <div className="relative h-96 lg:col-span-2 lg:h-150">
        {p.site ? (
          <GeofenceMap
            label="Site map: the boundary and where evidence was captured"
            pin={pin}
            corners={corners}
            mode="view"
            locked
            captures={visible.map((e) => ({
              lat: e.latitude!,
              lon: e.longitude!,
              inside:
                corners.length >= 3 ? insidePolygon({ lat: e.latitude!, lon: e.longitude! }, corners) : true,
              label: `EV-${shortId(e.id)} · ${formatDateTime(e.captured_at, timeZone)}`,
            }))}
            className="h-full w-full"
          />
        ) : (
          <Card className="flex h-full items-center justify-center p-6 text-slate">
            The site hasn&apos;t been pinned yet.
          </Card>
        )}
      </div>
      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-4 p-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.milestone} className="type-small font-semibold text-ink">
              Milestone
            </label>
            <select
              id={ids.milestone}
              value={milestoneId}
              onChange={(e) => setMilestoneId(e.target.value)}
              className="min-h-11 rounded-control border border-line-strong bg-white px-3 text-ink"
            >
              <option value="">All milestones</option>
              {ms.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="type-small mb-1 font-semibold text-ink">Show</legend>
            {(
              [
                ["supervisor", "Supervisor evidence"],
                ["contractor", "Contractor uploads"],
                ["review", "Under review"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex items-center justify-between gap-3 text-ink">
                <span className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={show[key]}
                    onChange={(e) => setShow({ ...show, [key]: e.target.checked })}
                  />
                  {label}
                </span>
                <span className="ibh-tabular type-small text-slate">{counts[key]}</span>
              </label>
            ))}
          </fieldset>
          <p className="type-small text-slate">
            Rejected captures don&apos;t appear here. The dashed line is the 25 m tolerance we allow for GPS
            drift.
          </p>
        </Card>
        <Card className="overflow-hidden">
          <h3 className="border-b border-line px-4 py-3 font-semibold text-ink">
            {visible.length} {visible.length === 1 ? "capture" : "captures"}
          </h3>
          {visible.length ? (
            <ul className="max-h-96 overflow-y-auto">
              {visible.map((e) => (
                <li key={e.id} className="flex flex-col gap-1 border-b border-line px-4 py-3 last:border-b-0">
                  <span className="flex items-center justify-between gap-2">
                    <span className="type-mono text-ink">EV-{shortId(e.id)}</span>
                    <StatusChip entity="evidence" state={e.status} audience="client" size="small" />
                  </span>
                  <span className="type-small text-slate">
                    {formatDateTime(e.captured_at, timeZone)} ·{" "}
                    {e.captured_by_role === "contractor" ? "Contractor" : "Supervisor"}
                    {e.accuracy_m != null ? ` · ±${Math.round(e.accuracy_m)} m` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="type-small p-4 text-slate">No captures to show.</p>
          )}
        </Card>
      </aside>
    </div>
  );
}
