"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { keys } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";
import type { ClientCurrency } from "@/common/money";

// The monthly supervision subscription (Stripe Billing). A project has none until the client starts one, so a
// 404 on the read means "not started", not an error. Nothing counts until Stripe confirms by webhook: after
// Checkout the page keeps reading until the status is `active`.

export type Subscription = components["schemas"]["SubscriptionOut"];

export const subscriptionKeys = {
  one: (projectId: string) => ["project", projectId, "subscription"] as const,
};

/** The project's subscription, or null when none was started (404 no_subscription). */
export function useSubscription(projectId: string, pollUntilActive = false) {
  return useQuery({
    queryKey: subscriptionKeys.one(projectId),
    refetchInterval: (query) => (pollUntilActive && query.state.data?.status !== "active" ? 3_000 : false),
    retry: false,
    queryFn: async (): Promise<Subscription | null> => {
      try {
        return await call(
          api().GET("/api/v1/projects/{project_id}/subscription", {
            params: { path: { project_id: projectId } },
          }),
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
  });
}

export function useStartSubscription(projectId: string) {
  return useWrite((currency: ClientCurrency, key: string) =>
    call(
      api().POST("/api/v1/projects/{project_id}/subscription", {
        params: { path: { project_id: projectId } },
        body: { currency },
        headers: { "Idempotency-Key": key },
      }),
    ),
  );
}

export function useCancelSubscription(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (_: null) =>
      call(
        api().POST("/api/v1/projects/{project_id}/subscription/cancel", {
          params: { path: { project_id: projectId } },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: subscriptionKeys.one(projectId) }) },
  );
}

/** Refresh what the subscription unlocks: the BoQ approval and the project's status (billing can pause it). */
export function useRefreshAfterSubscription(projectId: string) {
  const queries = useQueryClient();
  return useCallback(() => {
    void queries.invalidateQueries({ queryKey: keys.project(projectId) });
    void queries.invalidateQueries({ queryKey: ["project", projectId, "boq"] });
  }, [queries, projectId]);
}
