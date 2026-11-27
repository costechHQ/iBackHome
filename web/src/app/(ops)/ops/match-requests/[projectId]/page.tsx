import { environmentName } from "@/common/layout/shell-data";
import { MatchRequestDetail } from "@/features/ops-console/match-request-detail";

type Props = { params: Promise<{ projectId: string }> };

// Match requests (ADR 0007, phase 2): one request and the shortlist builder, by its project
export default async function MatchRequestPage({ params }: Props) {
  const { projectId } = await params;
  return <MatchRequestDetail projectId={projectId} environment={environmentName()} />;
}
