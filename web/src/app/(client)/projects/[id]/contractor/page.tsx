import { ContractorMatch } from "@/features/projects/contractor-match";

type Props = { params: Promise<{ id: string }> };

// Find a contractor (ADR 0007, phase 2)
export default async function Page({ params }: Props) {
  const { id } = await params;
  return <ContractorMatch projectId={id} />;
}
