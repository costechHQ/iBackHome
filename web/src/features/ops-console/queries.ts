"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { keys as shared } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

// The ops console's reads and its one write here: the queue, a dispute's audit trail, and the two-step resolve.

export type QueueDispute = components["schemas"]["DisputeItem"];
export type AuditEntry = components["schemas"]["AuditEntryOut"];

export const keys = {
  queue: () => ["ops", "queue"] as const,
  audit: (objectType: string, objectId: string) => ["ops", "audit", objectType, objectId] as const,
};

export function useOpsQueue() {
  return useQuery({ queryKey: keys.queue(), queryFn: () => call(api().GET("/api/v1/ops/queue")) });
}

/** Every audit entry for one object (first 200; a dispute or milestone has a handful). */
export function useAudit(objectType: "dispute" | "milestone", objectId: string | undefined) {
  return useQuery({
    queryKey: keys.audit(objectType, objectId ?? ""),
    enabled: Boolean(objectId),
    queryFn: async () => {
      const data = await call(
        api().GET("/api/v1/ops/audit", {
          params: { query: { object_type: objectType, object_id: objectId, limit: 200 } },
        }),
      );
      return data.items;
    },
  });
}

/** Propose (the first ops person) or confirm (a different one, same outcome). One Idempotency-Key per action. */
export function useResolve(dispute: { dispute_id: string; project_id: string; milestone_id: string }) {
  const queries = useQueryClient();
  return useWrite(
    (input: { outcome: "release" | "rework"; notes: string }, key: string) =>
      call(
        api().POST("/api/v1/disputes/{dispute_id}/resolve", {
          params: { path: { dispute_id: dispute.dispute_id } },
          body: input,
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: keys.queue() });
        void queries.invalidateQueries({ queryKey: ["ops", "audit"] });
        void queries.invalidateQueries({ queryKey: shared.milestones(dispute.project_id) });
        void queries.invalidateQueries({ queryKey: shared.ledger(dispute.project_id) });
      },
    },
  );
}
