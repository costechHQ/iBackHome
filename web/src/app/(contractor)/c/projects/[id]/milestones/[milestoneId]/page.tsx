import { SentBack } from "@/features/milestones/sent-back";

type Props = { params: Promise<{ id: string; milestoneId: string }> };

// WEB-CONTRACTOR-006
export default async function ContractorMilestonePage({ params }: Props) {
  const { id, milestoneId } = await params;
  return <SentBack projectId={id} milestoneId={milestoneId} />;
}
