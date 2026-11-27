"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys as shared } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

import type { MatchStatus } from "./matching";

// Ops' reads and writes for contractor matching (ADR 0007, phase 2): the queue (GET /ops/match-requests), the
// shortlist (POST /match-requests/{id}/shortlist) and cancelling. A request is read by its project
// (GET /projects/{id}/match-request, in common/api/queries). One Idempotency-Key per action.

export type MatchRequestItem = components["schemas"]["MatchRequestOpsItem"];

export const matchKeys = {
  all: ["ops", "match-requests"] as const,
  list: (status: MatchStatus) => ["ops", "match-requests", status] as const,
};

const PAGE = 100;

export function useMatchRequests(status: MatchStatus) {
  return useQuery({
    queryKey: matchKeys.list(status),
    queryFn: () =>
      call(api().GET("/api/v1/ops/match-requests", { params: { query: { status, limit: PAGE } } })),
  });
}

function useRefresh(projectId: string) {
  const queries = useQueryClient();
  return () => {
    void queries.invalidateQueries({ queryKey: matchKeys.all });
    void queries.invalidateQueries({ queryKey: shared.matchRequest(projectId) });
  };
}

export function useSetShortlist(requestId: string, projectId: string) {
  const refresh = useRefresh(projectId);
  return useWrite(
    (input: { contractorIds: string[]; note: string | null }, key: string) =>
      call(
        api().POST("/api/v1/match-requests/{request_id}/shortlist", {
          params: { path: { request_id: requestId } },
          body: { contractor_ids: input.contractorIds, note: input.note },
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: refresh },
  );
}

export function useCancelRequest(requestId: string, projectId: string) {
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
