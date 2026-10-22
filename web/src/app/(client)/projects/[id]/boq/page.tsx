import { BoqReview } from "@/features/projects/boq-review";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-005
export default async function Page({ params }: Props) {
  const { id } = await params;
  return <BoqReview projectId={id} />;
}
