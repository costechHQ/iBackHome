import { environmentName } from "@/common/layout/shell-data";
import { FlaggedEvidence } from "@/features/ops-console/evidence-review";

// WEB-OPS-005 (queue)
export default function FlaggedEvidencePage() {
  return <FlaggedEvidence evidenceId={null} environment={environmentName()} />;
}
