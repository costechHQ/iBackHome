import { SubscriptionPage } from "@/features/subscriptions/subscription";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ session_id?: string; cancelled?: string }>;
};

// The supervision subscription. Stripe sends the client back here with ?session_id or ?cancelled=1.
export default async function Page({ params, searchParams }: Props) {
  const { id } = await params;
  const { session_id, cancelled } = await searchParams;
  return (
    <SubscriptionPage projectId={id} returnedFromStripe={Boolean(session_id)} cancelled={cancelled === "1"} />
  );
}
