import { environmentName } from "@/common/layout/shell-data";
import { PriceIndex } from "@/features/ops-console/price-index";

// WEB-OPS-009
export default function Page() {
  return <PriceIndex environment={environmentName()} />;
}
