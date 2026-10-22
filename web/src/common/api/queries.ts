"use client";

import { useQuery } from "@tanstack/react-query";

import { readLedger, type LedgerEntry } from "../ledger";
import { api, call } from "./client";
import type { components, paths } from "./schema";

// Reads shared by the milestones and dashboard features, through the generated client and the same-origin
// proxy. Writes live with the screen that makes them (useWrite).

export type Project = components["schemas"]["ProjectDetail"];
export type Milestone = components["schemas"]["ProjectMilestoneOut"];
export type Evidence = components["schemas"]["GalleryItem"];

export const keys = {
  projects: () => ["projects"] as const,
  project: (id: string) => ["project", id] as const,
  milestones: (id: string) => ["project", id, "milestones"] as const,
  ledger: (id: string) => ["project", id, "ledger"] as const,
  evidence: (id: string, filters: EvidenceFilters) => ["project", id, "evidence", filters] as const,
};

/** The viewer's projects (a client's own, a contractor's, every project for ops); the first 200 is plenty. */
export function useProjects() {
  return useQuery({
    queryKey: keys.projects(),
    queryFn: () => call(api().GET("/api/v1/projects", { params: { query: { limit: 200 } } })),
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: keys.project(projectId),
    queryFn: () =>
      call(api().GET("/api/v1/projects/{project_id}", { params: { path: { project_id: projectId } } })),
  });
}

export function useMilestones(projectId: string) {
  return useQuery({
    queryKey: keys.milestones(projectId),
    queryFn: () =>
      call(
        api().GET("/api/v1/projects/{project_id}/milestones", {
          params: { path: { project_id: projectId } },
        }),
      ),
  });
}

/** Every ledger entry of the project (all pages), read into payments, releases and escrow now. */
export function useLedger(projectId: string) {
  return useQuery(ledgerQuery(projectId));
}

/** The ledger query itself, for screens that read several projects at once (useQueries). */
export function ledgerQuery(projectId: string) {
  return {
    queryKey: keys.ledger(projectId),
    queryFn: async () => {
      const entries: LedgerEntry[] = [];
      let cursor: string | undefined;
      for (let page = 0; page < 20; page++) {
        const data = await call(
          api().GET("/api/v1/projects/{project_id}/ledger", {
            params: { path: { project_id: projectId }, query: { limit: 200, cursor } },
          }),
        );
        entries.push(...data.items);
        if (!data.next_cursor) break;
        cursor = data.next_cursor;
      }
      return { entries, ledger: readLedger(projectId, entries) };
    },
  };
}

/** The gallery's filters, exactly as the API defines them. */
export type EvidenceFilters = Omit<
  NonNullable<paths["/api/v1/projects/{project_id}/evidence"]["get"]["parameters"]["query"]>,
  "cursor" | "limit"
>;

// Evidence read URLs are signed for 15 minutes: refresh the list well before they expire.
const EVIDENCE_REFRESH_MS = 10 * 60_000;

export function useEvidence(projectId: string, filters: EvidenceFilters = {}) {
  return useQuery({
    queryKey: keys.evidence(projectId, filters),
    queryFn: async () => {
      const items: Evidence[] = [];
      let cursor: string | undefined;
      for (let page = 0; page < 10; page++) {
        const data = await call(
          api().GET("/api/v1/projects/{project_id}/evidence", {
            params: { path: { project_id: projectId }, query: { ...filters, limit: 100, cursor } },
          }),
        );
        items.push(...data.items);
        if (!data.next_cursor) break;
        cursor = data.next_cursor;
      }
      return items;
    },
    staleTime: EVIDENCE_REFRESH_MS,
    refetchInterval: EVIDENCE_REFRESH_MS,
  });
}

/** A short, stable label for an id the design shows as a reference (EV-…, R-…): the backend has none yet. */
export function shortId(id: string): string {
  return id.slice(0, 8);
}
