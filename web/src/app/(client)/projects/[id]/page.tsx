import { notFound, redirect } from "next/navigation";

import { attentionMilestoneId } from "@/features/milestones/server";

type Props = { params: Promise<{ id: string }> };

// Until the project overview (WEB-CLIENT-009) exists, a project opens on the milestone that needs attention.
export default async function ProjectPage({ params }: Props) {
  const { id } = await params;
  const milestoneId = await attentionMilestoneId(id);
  if (!milestoneId) notFound();
  redirect(`/projects/${id}/milestones/${milestoneId}`);
}
