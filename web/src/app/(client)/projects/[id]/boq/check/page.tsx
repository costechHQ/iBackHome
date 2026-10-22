import { QuoteChecker } from "@/features/projects/quote-check";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-006
export default async function Page({ params }: Props) {
  const { id } = await params;
  return <QuoteChecker projectId={id} />;
}
