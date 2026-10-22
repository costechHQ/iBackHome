import { environmentName } from "@/common/layout/shell-data";
import { OpsProjectDetail } from "@/features/ops-console/project-detail";

type Props = { params: Promise<{ id: string }> };

// WEB-OPS-004 (detail)
export default async function OpsProjectPage({ params }: Props) {
  const { id } = await params;
  return <OpsProjectDetail projectId={id} environment={environmentName()} />;
}
