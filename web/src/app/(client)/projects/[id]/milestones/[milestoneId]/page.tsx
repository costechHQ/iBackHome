import { MilestoneDetail } from "@/features/milestones/detail";

type Props = { params: Promise<{ id: string; milestoneId: string }> };

// WEB-CLIENT-013
export default async function MilestonePage({ params }: Props) {
  const { id, milestoneId } = await params;
  return <MilestoneDetail projectId={id} milestoneId={milestoneId} />;
}
