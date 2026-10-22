import { Receipt } from "@/features/milestones/receipt";

type Props = { params: Promise<{ id: string; milestoneId: string }> };

// WEB-CLIENT-014 receipt (prints to PDF)
export default async function ReceiptPage({ params }: Props) {
  const { id, milestoneId } = await params;
  return <Receipt projectId={id} milestoneId={milestoneId} />;
}
