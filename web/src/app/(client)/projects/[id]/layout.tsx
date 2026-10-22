import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { ProjectHeader } from "@/common/layout/client-shell";
import { projectHeader } from "@/features/milestones/server";

type Props = { children: ReactNode; params: Promise<{ id: string }> };

// One project: its title row and tabs above every project screen.
export default async function ProjectLayout({ children, params }: Props) {
  const { id } = await params;
  const header = await projectHeader(id);
  if (!header) notFound();
  return (
    <>
      <ProjectHeader
        id={header.id}
        title={header.title}
        status={header.status}
        address={header.address}
        badges={{ Milestones: header.needsApproval }}
      />
      {children}
    </>
  );
}
