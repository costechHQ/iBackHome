import { LedgerPage } from "@/features/dashboard/ledger";

type Props = { params: Promise<{ id: string }> };

// WEB-CLIENT-017
export default async function ProjectLedgerPage({ params }: Props) {
  const { id } = await params;
  return <LedgerPage projectId={id} />;
}
