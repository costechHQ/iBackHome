"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys as shared } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

import { keys as opsKeys } from "./queries";

// Reads and writes for vetting, choosing a supervisor and spot checks (W8b), through the ops routes added for
// the console (backend #78): GET /supervisors/{id}/application, GET /supervisors, GET /projects/{id}/spot-checks,
// and the existing writes. One Idempotency-Key per action.

export type Application = components["schemas"]["SupervisorApplicationOut"];
export type SupervisorRow = components["schemas"]["SupervisorListItem"];
export type SpotCheck = components["schemas"]["SpotCheckOut"];
type VettingDecision = components["schemas"]["VettingDecision"];

export const supervisionKeys = {
  application: (id: string) => ["ops", "supervisors", "application", id] as const,
  list: (status: string, projectId: string | null) => ["ops", "supervisors", status, projectId] as const,
  spotChecks: (projectId: string) => ["ops", "spot-checks", projectId] as const,
};

export function useApplication(supervisorId: string) {
  return useQuery({
    queryKey: supervisionKeys.application(supervisorId),
    queryFn: () =>
      call(
        api().GET("/api/v1/supervisors/{supervisor_id}/application", {
          params: { path: { supervisor_id: supervisorId } },
        }),
      ),
  });
}

export function useSupervisors(projectId: string | null, status: "approved" | "pending" = "approved") {
  return useQuery({
    queryKey: supervisionKeys.list(status, projectId),
    queryFn: () =>
      call(
        api().GET("/api/v1/supervisors", {
          params: { query: { vetting_status: status, project_id: projectId ?? undefined } },
        }),
      ),
  });
}

/** The spot-check query itself, for screens that read several projects at once (useQueries). */
export function spotChecksQuery(projectId: string) {
  return {
    queryKey: supervisionKeys.spotChecks(projectId),
    queryFn: () =>
      call(
        api().GET("/api/v1/projects/{project_id}/spot-checks", {
          params: { path: { project_id: projectId } },
        }),
      ),
  };
}

export function useSpotChecks(projectId: string) {
  return useQuery(spotChecksQuery(projectId));
}

export function useVet(supervisorId: string) {
  const queries = useQueryClient();
  return useWrite(
    (body: VettingDecision, key: string) =>
      call(
        api().POST("/api/v1/supervisors/{supervisor_id}/vetting", {
          params: { path: { supervisor_id: supervisorId } },
          body,
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: supervisionKeys.application(supervisorId) });
        void queries.invalidateQueries({ queryKey: ["ops", "supervisors"] });
        void queries.invalidateQueries({ queryKey: opsKeys.queue() });
      },
    },
  );
}

export function useAssign(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (supervisorId: string, key: string) =>
      call(
        api().POST("/api/v1/projects/{project_id}/supervisor", {
          params: { path: { project_id: projectId } },
          body: { supervisor_id: supervisorId },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: ["ops", "supervisors"] });
        void queries.invalidateQueries({ queryKey: shared.project(projectId) });
        void queries.invalidateQueries({ queryKey: shared.projects() });
      },
    },
  );
}

export function useScheduleSpotCheck() {
  const queries = useQueryClient();
  return useWrite(
    (input: { projectId: string; supervisorId: string; scheduledFor: string }, key: string) =>
      call(
        api().POST("/api/v1/projects/{project_id}/spot-checks", {
          params: { path: { project_id: input.projectId } },
          body: { supervisor_id: input.supervisorId, scheduled_for: input.scheduledFor },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: (_data, _error, input) =>
        void queries.invalidateQueries({ queryKey: supervisionKeys.spotChecks(input.projectId) }),
    },
  );
}
