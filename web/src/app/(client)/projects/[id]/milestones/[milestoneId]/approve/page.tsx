import { ApproveFlow } from "@/features/milestones/approve";

type Props = { params: Promise<{ id: string; milestoneId: string }> };

// WEB-CLIENT-014 (phone flow: review, then confirm)
export default async function ApprovePage({ params }: Props) {
  const { id, milestoneId } = await params;
  return <ApproveFlow projectId={id} milestoneId={milestoneId} />;
}
