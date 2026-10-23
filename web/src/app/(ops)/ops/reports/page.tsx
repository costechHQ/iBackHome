import { environmentName } from "@/common/layout/shell-data";
import { ReportsReview } from "@/features/ops-console/reports-review";

// WEB-OPS-010
export default function Page() {
  return <ReportsReview environment={environmentName()} />;
}
