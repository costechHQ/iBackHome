"use client";

import { useQueries } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { useProjectsWithMilestones } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { projectKeys } from "@/features/projects/api";

import { nowText, projectFlags, type Flag } from "./ops";

// Every project with what ops needs to know about it (WEB-OPS-002, 004): its milestones, what is happening now,
// and its flags. The BoQ is read only for projects in BoQ review (to know whether ops still has to approve).

export type OpsProjectRow = {
  project: components["schemas"]["ProjectOut"];
  now: string;
  flags: Flag[];
  milestones: number;
  released: number;
};

export function useOpsProjects() {
  const data = useProjectsWithMilestones();
  const inReview = data.items.filter((i) => i.project.status === "boq_review").map((i) => i.project.id);
  const boqs = useQueries({
    queries: inReview.map((id) => ({
      queryKey: projectKeys.boq(id),
      queryFn: () =>
        call(api().GET("/api/v1/projects/{project_id}/boq", { params: { path: { project_id: id } } })),
    })),
  });
  const opsMissing = new Map(
    inReview.map((id, i) => [id, boqs[i]?.data?.approvals_missing.includes("ops") ?? false]),
  );
  const rows: OpsProjectRow[] = data.items.map(({ project, milestones }) => ({
    project,
    now: nowText(project, milestones),
    flags: projectFlags(project, milestones, opsMissing.get(project.id) ?? false),
    milestones: milestones.length,
    released: milestones.filter((m) => m.status === "released").length,
  }));
  return {
    rows,
    isPending: data.isPending || boqs.some((q) => q.isPending),
    error: data.error,
    refetch: data.refetch,
  };
}
