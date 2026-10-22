"use client";

import { useMemo } from "react";

import { useLedger, useMilestones, useProject, type Milestone, type Project } from "@/common/api/queries";
import { escrowNow, moneyByMilestone, type EscrowNow, type MilestoneMoney } from "@/common/ledger";

export type MilestoneView = {
  project: Project;
  milestones: Milestone[];
  milestone: Milestone;
  /** This milestone's payment and release, from the ledger (see common/ledger.ts). */
  money: MilestoneMoney;
  escrow: EscrowNow;
};

/** Everything one milestone's screens need, from three reads. */
export function useMilestone(projectId: string, milestoneId: string) {
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const ledger = useLedger(projectId);

  const view = useMemo((): MilestoneView | null => {
    if (!project.data || !milestones.data || !ledger.data) return null;
    const milestone = milestones.data.find((m) => m.id === milestoneId);
    if (!milestone) return null;
    const byMilestone = moneyByMilestone(milestones.data, ledger.data.ledger);
    return {
      project: project.data,
      milestones: milestones.data,
      milestone,
      money: byMilestone.get(milestone.id) ?? {},
      escrow: escrowNow(milestones.data, ledger.data.ledger, byMilestone),
    };
  }, [project.data, milestones.data, ledger.data, milestoneId]);

  const error = project.error ?? milestones.error ?? ledger.error;
  const loading = !error && (project.isPending || milestones.isPending || ledger.isPending);
  const missing = !loading && !error && !view;
  return {
    view,
    error,
    loading,
    missing,
    refetch: () => Promise.all([milestones.refetch(), ledger.refetch()]),
  };
}
