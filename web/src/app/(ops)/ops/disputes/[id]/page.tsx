import { environmentName } from "@/common/layout/shell-data";
import { DisputeDetail } from "@/features/ops-console/dispute-detail";

type Props = { params: Promise<{ id: string }> };

// WEB-OPS-006 (resolution)
export default async function DisputePage({ params }: Props) {
  const { id } = await params;
  return <DisputeDetail disputeId={id} environment={environmentName()} />;
}
