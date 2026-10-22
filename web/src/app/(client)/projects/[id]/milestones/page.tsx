import { MilestoneList } from "@/features/milestones/list";

type Props = { params: Promise<{ id: string }> };

export default async function MilestonesPage({ params }: Props) {
  const { id } = await params;
  return <MilestoneList projectId={id} />;
}
