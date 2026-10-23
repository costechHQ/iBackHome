import { environmentName } from "@/common/layout/shell-data";
import { AuditLog } from "@/features/ops-console/audit-log";

// WEB-OPS-011
export default function Page() {
  return <AuditLog environment={environmentName()} />;
}
