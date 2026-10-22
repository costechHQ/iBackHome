import { environmentName } from "@/common/layout/shell-data";
import { OpsOverview } from "@/features/ops-console/overview";

// WEB-OPS-002
export default function OpsHome() {
  return <OpsOverview environment={environmentName()} />;
}
