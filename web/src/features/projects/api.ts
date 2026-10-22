"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

// Reads and writes for setting a project up (WEB-CLIENT-003 to 006). Each write sends one Idempotency-Key per
// action. The backend decides: site changes only while draft or BoQ review (409 site_locked), the final BoQ
// approval needs a saved site (409 site_not_set).

export type Boq = components["schemas"]["BoqOut"];
export type QuoteCheck = components["schemas"]["QuoteCheckOut"];
export type IndexPrice = components["schemas"]["CurrentPrice"];

export const projectKeys = {
  boq: (id: string) => ["project", id, "boq"] as const,
  priceIndex: () => ["price-index"] as const,
};

export function useBoq(projectId: string, enabled = true) {
  return useQuery({
    queryKey: projectKeys.boq(projectId),
    enabled,
    queryFn: () =>
      call(api().GET("/api/v1/projects/{project_id}/boq", { params: { path: { project_id: projectId } } })),
  });
}

export function usePriceIndex() {
  return useQuery({
    queryKey: projectKeys.priceIndex(),
    staleTime: 10 * 60_000,
    queryFn: () => call(api().GET("/api/v1/price-index")),
  });
}

export function useCreateProject() {
  const queries = useQueryClient();
  return useWrite(
    (body: components["schemas"]["ProjectCreate"], key: string) =>
      call(api().POST("/api/v1/projects", { body, headers: { "Idempotency-Key": key } })),
    { onSuccess: () => void queries.invalidateQueries({ queryKey: keys.projects() }) },
  );
}

export function useSaveSite(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (body: components["schemas"]["SiteSet"], key: string) =>
      call(
        api().PUT("/api/v1/projects/{project_id}/site", {
          params: { path: { project_id: projectId } },
          body,
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: keys.project(projectId) }) },
  );
}

export function useApproveBoq(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (_: null, key: string) =>
      call(
        api().POST("/api/v1/projects/{project_id}/boq/approve", {
          params: { path: { project_id: projectId } },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: projectKeys.boq(projectId) });
        void queries.invalidateQueries({ queryKey: keys.project(projectId) });
        void queries.invalidateQueries({ queryKey: keys.milestones(projectId) });
        void queries.invalidateQueries({ queryKey: keys.projects() });
      },
    },
  );
}

/** The quote check: the model reads the lines, plain code compares them with the index. */
export function useQuoteCheck() {
  return useWrite((body: components["schemas"]["QuoteCheckIn"], key: string) =>
    call(api().POST("/api/v1/quotes/check", { body, headers: { "Idempotency-Key": key } })),
  );
}
