import { environmentName } from "@/common/layout/shell-data";
import { MatchRequestsQueue } from "@/features/ops-console/match-requests-queue";

// Match requests (ADR 0007, phase 2): the queue
export default function Page() {
  return <MatchRequestsQueue environment={environmentName()} />;
}
