"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";

// Reads and writes for contractor applications, vetting and the directory (ADR 0007, phase 1), through the
// ops routes: GET /contractor-applications (+ /{id}), POST /contractor-applications/{id}/decision and
// GET /contractors. One Idempotency-Key per action.

export type ContractorApplication = components["schemas"]["ContractorApplicationOut"];
export type ContractorApplicationItem = components["schemas"]["ContractorApplicationListItem"];
export type Contractor = components["schemas"]["ContractorOut"];
export type ContractorDecision = components["schemas"]["ContractorDecisionIn"];
export type ApplicationStatus = "pending" | "approved" | "rejected";

export const contractorKeys = {
  all: ["ops", "contractors"] as const,
  applications: (status: ApplicationStatus) => ["ops", "contractors", "applications", status] as const,
  application: (id: string) => ["ops", "contractors", "application", id] as const,
  directory: (state: string, specialty: string, listed: boolean | null) =>
    ["ops", "contractors", "directory", state, specialty, listed] as const,
};

const PAGE = 100; // the first 100; a pilot queue is far smaller

export function useContractorApplications(status: ApplicationStatus) {
  return useQuery({
    queryKey: contractorKeys.applications(status),
    queryFn: () =>
      call(api().GET("/api/v1/contractor-applications", { params: { query: { status, limit: PAGE } } })),
  });
}

export function useContractorApplication(id: string) {
  return useQuery({
    queryKey: contractorKeys.application(id),
    queryFn: () =>
      call(
        api().GET("/api/v1/contractor-applications/{application_id}", {
          params: { path: { application_id: id } },
        }),
      ),
  });
}

export function useContractorDirectory(state: string, specialty: string, listed: boolean | null = null) {
  return useQuery({
    queryKey: contractorKeys.directory(state, specialty, listed),
    queryFn: () =>
      call(
        api().GET("/api/v1/contractors", {
          params: {
            query: {
              state: state || undefined,
              specialty: specialty || undefined,
              listed: listed ?? undefined,
              limit: PAGE,
            },
          },
        }),
      ),
  });
}

export function useDecideContractor(id: string) {
  const queries = useQueryClient();
  return useWrite(
    (body: ContractorDecision, key: string) =>
      call(
        api().POST("/api/v1/contractor-applications/{application_id}/decision", {
          params: { path: { application_id: id } },
          body,
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: contractorKeys.all }) },
  );
}
