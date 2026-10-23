import { environmentName } from "@/common/layout/shell-data";
import { OpsProjects } from "@/features/ops-console/projects";

// WEB-OPS-004 (list)
export default function Page() {
  return <OpsProjects environment={environmentName()} />;
}
