import { FundMilestone } from "@/features/milestones/fund";

type Props = {
  params: Promise<{ id: string; milestoneId: string }>;
  searchParams: Promise<{ session_id?: string; cancelled?: string }>;
};

// WEB-CLIENT-007 / 016. Stripe sends the client back here with ?session_id or ?cancelled=1.
export default async function FundPage({ params, searchParams }: Props) {
  const { id, milestoneId } = await params;
  const { session_id, cancelled } = await searchParams;
  return (
    <FundMilestone
      projectId={id}
      milestoneId={milestoneId}
      sessionId={session_id ?? null}
      cancelled={cancelled === "1"}
    />
  );
}
