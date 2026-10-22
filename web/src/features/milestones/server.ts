import "server-only";

import { serverApi } from "@/common/api/server";

import { milestoneNeedingAttention } from "./attention";

// Server-side reads for the project routes (never cached). They return null when the project isn't the viewer's
// or doesn't exist, so the route answers 404 either way.

export async function projectHeader(projectId: string) {
  const api = await serverApi();
  const [project, milestones] = await Promise.all([
    api.GET("/api/v1/projects/{project_id}", { params: { path: { project_id: projectId } } }),
    api.GET("/api/v1/projects/{project_id}/milestones", { params: { path: { project_id: projectId } } }),
  ]);
  if (!project.data) return null;
  return {
    id: project.data.id,
    title: project.data.title,
    status: project.data.status,
    address: project.data.address,
    // The Milestones badge counts what needs the client: verified milestones waiting for approval.
    needsApproval: (milestones.data ?? []).filter((m) => m.status === "verified").length,
  };
}

/** Where /projects/:id goes until the project overview (WEB-CLIENT-009) exists. */
export async function attentionMilestoneId(projectId: string): Promise<string | null> {
  const api = await serverApi();
  const { data } = await api.GET("/api/v1/projects/{project_id}/milestones", {
    params: { path: { project_id: projectId } },
  });
  return data ? (milestoneNeedingAttention(data)?.id ?? null) : null;
}
