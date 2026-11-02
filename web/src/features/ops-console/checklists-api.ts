"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

// Ops' checklist per kind of milestone (P7): GET and PUT /checklist-templates. A saved list is copied into
// milestones made afterwards; milestones that already exist keep theirs.

export type ChecklistTemplate = components["schemas"]["ChecklistTemplateOut"];

const key = ["ops", "checklist-templates"] as const;

export function useChecklistTemplates() {
  return useQuery({ queryKey: key, queryFn: () => call(api().GET("/api/v1/checklist-templates")) });
}

export function useSaveChecklist() {
  const queries = useQueryClient();
  return useWrite(
    (input: { milestone_name: string; items: string[] }, idempotencyKey: string) =>
      call(
        api().PUT("/api/v1/checklist-templates", {
          body: input,
          headers: { "Idempotency-Key": idempotencyKey },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: key }) },
  );
}
