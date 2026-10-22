import { environmentName } from "@/common/layout/shell-data";
import { DisputeQueue } from "@/features/ops-console/dispute-queue";

// WEB-OPS-006 (queue)
export default function DisputesPage() {
  return <DisputeQueue environment={environmentName()} />;
}
