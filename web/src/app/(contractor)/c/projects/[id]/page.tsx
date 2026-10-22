import { redirect } from "next/navigation";

import { projectHeader } from "@/features/milestones/server";

type Props = { params: Promise<{ id: string }> };

// The contractor's project opens on its BoQ while it's being set up, then on its milestones.
export default async function ContractorProjectPage({ params }: Props) {
  const { id } = await params;
  const header = await projectHeader(id);
  const settingUp = header?.status === "draft" || header?.status === "boq_review";
  redirect(`/c/projects/${id}/${settingUp ? "boq" : "milestones"}`);
}
