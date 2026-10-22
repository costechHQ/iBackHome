import "server-only";

import { serverApi } from "../api/server";
import type { ProjectSummary } from "./client-shell";
import type { QueueCounts } from "./ops-shell";

// Data the portal shells need on every page, read on the server per request (never cached). A failure here
// must not take the page down: the shell then shows without the switcher or the counts.

/** The client's projects for the switcher (the first 200 is plenty for one client). */
export async function clientProjects(): Promise<ProjectSummary[]> {
  const api = await serverApi();
  const { data } = await api
    .GET("/api/v1/projects", { params: { query: { limit: 200 } } })
    .catch(() => ({ data: undefined }));
  return (data?.items ?? []).map((p) => ({ id: p.id, title: p.title }));
}

/** Items waiting in each ops queue, for the sidebar badges. */
export async function opsQueueCounts(): Promise<QueueCounts | null> {
  const api = await serverApi();
  const { data } = await api.GET("/api/v1/ops/queue").catch(() => ({ data: undefined }));
  if (!data) return null;
  return {
    vetting: data.vetting.length,
    flagged_evidence: data.flagged_evidence.length,
    disputes: data.disputes.length,
  };
}

/** Which environment this is, for the ops badge (set by Docker Compose; LOCAL when unset). */
export function environmentName(): string {
  return process.env.IBH_ENVIRONMENT ?? "local";
}
