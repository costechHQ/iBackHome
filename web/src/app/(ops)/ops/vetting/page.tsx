import { environmentName } from "@/common/layout/shell-data";
import { VettingQueue } from "@/features/ops-console/vetting-queue";

// WEB-OPS-003 (queue)
export default function Page() {
  return <VettingQueue environment={environmentName()} />;
}
