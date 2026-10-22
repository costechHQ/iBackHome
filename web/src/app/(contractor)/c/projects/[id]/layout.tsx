import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { ContractorProjectHeader } from "@/common/layout/contractor-shell";
import { projectHeader } from "@/features/milestones/server";

type Props = { children: ReactNode; params: Promise<{ id: string }> };

// One of the contractor's projects: the project row above every project screen.
export default async function ContractorProjectLayout({ children, params }: Props) {
  const { id } = await params;
  const header = await projectHeader(id);
  if (!header) notFound();
  return (
    <>
      <ContractorProjectHeader id={header.id} title={header.title} status={header.status} />
      {children}
    </>
  );
}
