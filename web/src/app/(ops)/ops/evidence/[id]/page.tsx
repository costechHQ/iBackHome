import { environmentName } from "@/common/layout/shell-data";
import { FlaggedEvidence } from "@/features/ops-console/evidence-review";

type Props = { params: Promise<{ id: string }> };

// WEB-OPS-005 (review)
export default async function FlaggedEvidenceReviewPage({ params }: Props) {
  const { id } = await params;
  return <FlaggedEvidence evidenceId={id} environment={environmentName()} />;
}
