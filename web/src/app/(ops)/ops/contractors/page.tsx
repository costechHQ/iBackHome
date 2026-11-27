import { environmentName } from "@/common/layout/shell-data";
import { ContractorsQueue } from "@/features/ops-console/contractors-queue";

// Contractors (ADR 0007, phase 1): the applications and the directory
export default function Page() {
  return <ContractorsQueue environment={environmentName()} />;
}
