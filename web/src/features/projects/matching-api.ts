"use client";

import { useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";

import type { MatchBrief } from "./matching";

// The client's writes for contractor matching (ADR 0007, phase 2). One Idempotency-Key per action. The backend
// decides: the project must be a draft with no contractor, one open request per project, and a choice must be
// one of the shortlisted contractors.

function useRefresh(projectId: string) {
  const queries = useQueryClient();
  return () => {
    void queries.invalidateQueries({ queryKey: keys.matchRequest(projectId) });
    void queries.invalidateQueries({ queryKey: keys.project(projectId) });
    void queries.invalidateQueries({ queryKey: keys.projects() });
  };
}

export function useRequestMatch(projectId: string) {
  const refresh = useRefresh(projectId);
  return useWrite(
    (brief: MatchBrief, key: string) =>
      call(
        api().POST("/api/v1/projects/{project_id}/match-request", {
          params: { path: { project_id: projectId } },
          body: brief,
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: refresh },
  );
}

export function useChooseContractor(projectId: string, requestId: string) {
  const refresh = useRefresh(projectId);
  return useWrite(
    (contractorId: string, key: string) =>
      call(
        api().POST("/api/v1/match-requests/{request_id}/choose", {
          params: { path: { request_id: requestId } },
          body: { contractor_id: contractorId },
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: refresh },
  );
}

export function useCancelMatch(projectId: string, requestId: string) {
  const refresh = useRefresh(projectId);
  return useWrite(
    (reason: string | null, key: string) =>
      call(
        api().POST("/api/v1/match-requests/{request_id}/cancel", {
          params: { path: { request_id: requestId } },
          body: { reason },
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: refresh },
  );
}
