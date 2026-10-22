import { ContractorMilestones } from "@/features/milestones/contractor-milestones";

type Props = { params: Promise<{ id: string }> };

// WEB-CONTRACTOR-005
export default async function ContractorMilestonesPage({ params }: Props) {
  const { id } = await params;
  return <ContractorMilestones projectId={id} />;
}
