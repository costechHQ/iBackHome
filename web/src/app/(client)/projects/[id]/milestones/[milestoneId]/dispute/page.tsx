import { DisputeScreen } from "@/features/milestones/dispute";

type Props = { params: Promise<{ id: string; milestoneId: string }> };

// WEB-CLIENT-015
export default async function DisputePage({ params }: Props) {
  const { id, milestoneId } = await params;
  return <DisputeScreen projectId={id} milestoneId={milestoneId} />;
}
