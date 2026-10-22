import { notFound, redirect } from "next/navigation";

import { isSettingUp } from "@/common/layout/nav";
import { ProjectOverview } from "@/features/dashboard/project-overview";
import { projectHeader } from "@/features/milestones/server";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-009 Project overview; a project still being set up opens its set-up tracker (WEB-CLIENT-003).
export default async function ProjectPage({ params }: Props) {
  const { id } = await params;
  const header = await projectHeader(id);
  if (!header) notFound();
  if (isSettingUp(header.status)) redirect(`/projects/${id}/setup`);
  return <ProjectOverview projectId={id} />;
}
