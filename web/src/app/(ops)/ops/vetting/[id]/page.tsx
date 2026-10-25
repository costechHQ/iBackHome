import { environmentName } from "@/common/layout/shell-data";
import { VettingDetail } from "@/features/ops-console/vetting-detail";

type Props = { params: Promise<{ id: string }> };

// WEB-OPS-003 (application and decision)
export default async function VettingDetailPage({ params }: Props) {
  const { id } = await params;
  return <VettingDetail supervisorId={id} environment={environmentName()} />;
}
