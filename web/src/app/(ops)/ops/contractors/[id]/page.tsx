import { environmentName } from "@/common/layout/shell-data";
import { ContractorDetail } from "@/features/ops-console/contractor-detail";

type Props = { params: Promise<{ id: string }> };

// Contractors (ADR 0007, phase 1): one application and the decision
export default async function ContractorDetailPage({ params }: Props) {
  const { id } = await params;
  return <ContractorDetail applicationId={id} environment={environmentName()} />;
}
