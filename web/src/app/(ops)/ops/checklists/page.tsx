import { environmentName } from "@/common/layout/shell-data";
import { Checklists } from "@/features/ops-console/checklists-screen";

// Checklists per kind of milestone (P7)
export default function Page() {
  return <Checklists environment={environmentName()} />;
}
