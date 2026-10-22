import { ContractorBoq } from "@/features/projects/boq-editor";

type Props = { params: Promise<{ id: string }> };

// WEB-CONTRACTOR-004
export default async function ContractorBoqPage({ params }: Props) {
  const { id } = await params;
  return <ContractorBoq projectId={id} />;
}
