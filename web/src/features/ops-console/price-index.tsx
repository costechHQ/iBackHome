"use client";

import { ChartLine } from "lucide-react";
import { useState } from "react";

import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDate } from "@/common/time";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";
import { usePriceIndex } from "@/features/projects/api";

// WEB-OPS-009 Price index at /ops/price-index, read-only: each item's index price (the median of the suppliers'
// latest prices), the range, how many suppliers, when it was last seen and whether it's stale (older than 14
// days). Adding items, changing prices, supplier price changes and reminders need MX-16 (PACKAGE-REPORT W-46).
// The index is loaded from the survey CSV (features/price_index/load_survey.py).

type Tab = "all" | "stale";

export function PriceIndex({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const index = usePriceIndex();
  const [tab, setTab] = useState<Tab>("all");
  const header = <OpsHeader title="Price index · Enugu" environment={environment} />;

  if (index.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the price index">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (!index.data) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void index.refetch()} />
      </>
    );
  }
  const items = [...index.data].sort((a, b) => a.item.localeCompare(b.item));
  const stale = items.filter((i) => i.stale).length;
  const shown = tab === "stale" ? items.filter((i) => i.stale) : items;

  return (
    <>
      {header}
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center gap-4">
          <SegmentedControl
            label="Which items"
            value={tab}
            onChange={setTab}
            segments={[
              { value: "all", label: "All", count: items.length },
              { value: "stale", label: "Stale", count: stale },
            ]}
          />
          <p className="type-small text-slate">
            Stale = not updated for more than 14 days. Quote checks and order hints use these prices; a line
            more than 15% above is flagged to the client.
          </p>
        </div>
        {shown.length ? (
          <Table caption="Price index" dense>
            <thead>
              <tr>
                <Th>Item</Th>
                <Th>Unit</Th>
                <Th numeric>Price</Th>
                <Th numeric>Range</Th>
                <Th numeric>Suppliers</Th>
                <Th>Last seen</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {shown.map((i) => (
                <Tr key={i.item_key}>
                  <Td className="font-semibold text-ink">{i.item}</Td>
                  <Td>{i.unit}</Td>
                  <Td numeric>{formatMoney(i.price_minor, i.currency)}</Td>
                  <Td numeric className="text-slate">
                    {formatMoney(i.low_minor, i.currency)} – {formatMoney(i.high_minor, i.currency)}
                  </Td>
                  <Td numeric>{i.supplier_count}</Td>
                  <Td>{formatDate(i.last_observed_on, timeZone)}</Td>
                  <Td>
                    <ToneChip
                      label={i.stale ? "Stale" : "Current"}
                      tone={i.stale ? "warn" : "ok"}
                      size="small"
                    />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <Card>
            <EmptyState icon={ChartLine} title={tab === "stale" ? "Nothing is stale" : "The index is empty"}>
              {tab === "stale"
                ? "Every price was seen in the last 14 days."
                : "Prices are loaded from the supplier survey. Until then, quote checks say “not in the index”."}
            </EmptyState>
          </Card>
        )}
      </div>
    </>
  );
}
