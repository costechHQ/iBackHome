"use client";

import { useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";

// The contractor's claim, and the client's two decisions on a verified milestone. Each sends one Idempotency-Key per action (the same key on
// "Try again"), so a retry after a lost answer never approves or disputes twice. The backend decides: approve
// needs a verified milestone and no open dispute (409 otherwise), and asks escrow to release in the same step.

export function useApprove(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (milestoneId: string, key: string) =>
      call(
        api().POST("/api/v1/milestones/{milestone_id}/approve", {
          params: { path: { milestone_id: milestoneId } },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: keys.milestones(projectId) });
        void queries.invalidateQueries({ queryKey: keys.ledger(projectId) });
      },
    },
  );
}

export function useRaiseDispute(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (input: { milestoneId: string; reason: string }, key: string) =>
      call(
        api().POST("/api/v1/milestones/{milestone_id}/disputes", {
          params: { path: { milestone_id: input.milestoneId } },
          body: { reason: input.reason },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => void queries.invalidateQueries({ queryKey: keys.milestones(projectId) }),
    },
  );
}

/** The contractor says the work is finished: funded -> claimed (the project must be active; 409 otherwise). */
export function useClaim(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (milestoneId: string, key: string) =>
      call(
        api().POST("/api/v1/milestones/{milestone_id}/claim", {
          params: { path: { milestone_id: milestoneId } },
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: keys.milestones(projectId) }) },
  );
}
