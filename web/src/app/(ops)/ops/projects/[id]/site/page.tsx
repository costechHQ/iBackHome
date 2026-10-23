import { OpsHeader } from "@/common/layout/ops-shell";
import { environmentName } from "@/common/layout/shell-data";
import { SiteEditor } from "@/features/projects/site-editor";

type Props = { params: Promise<{ id: string }> };

// WEB-OPS-004: ops change a project's site (allowed at any time; every change is audited).
export default async function OpsSitePage({ params }: Props) {
  const { id } = await params;
  return (
    <>
      <OpsHeader title="Change site" environment={environmentName()} />
      <SiteEditor projectId={id} ops />
    </>
  );
}
