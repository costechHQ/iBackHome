import { notFound, redirect } from "next/navigation";

import { isSettingUp } from "@/common/layout/nav";
import { attentionMilestoneId, projectHeader } from "@/features/milestones/server";

type Props = { params: Promise<{ id: string }> };

// A project being set up opens on its set-up tracker; otherwise, until the project overview (WEB-CLIENT-009,
// W6b) exists, on the milestone that needs attention.
export default async function ProjectPage({ params }: Props) {
  const { id } = await params;
  const header = await projectHeader(id);
  if (!header) notFound();
  if (isSettingUp(header.status)) redirect(`/projects/${id}/setup`);
  const milestoneId = await attentionMilestoneId(id);
  redirect(milestoneId ? `/projects/${id}/milestones/${milestoneId}` : `/projects/${id}/setup`);
}
