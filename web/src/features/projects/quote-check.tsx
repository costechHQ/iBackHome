"use client";

import { FileText, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useViewerTimeZone } from "@/common/layout/online";
import { formatMoney } from "@/common/money";
import { formatDate } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { SegmentedControl } from "@/common/ui/segmented";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { useBoq, usePriceIndex, useQuoteCheck, type QuoteCheck } from "./api";
import { boqAsQuoteText, counts, flaggedFirst, overIndexTotal } from "./quote";

// WEB-CLIENT-006 Quote checker at /projects/:id/boq/check: the submitted BoQ (sent as text) or a quote PDF,
// checked against the Enugu price index. The model only reads the lines; plain code flags prices more than the
// threshold above the index, and every figure comes from the quote or the index. The design's quantity range
// check and step-by-step progress aren't in the backend, so a check shows one "Checking" state (W-31). Results
// aren't kept: they show until the page is left. Advisory only, labelled AI.

const MAX_PDF_BYTES = 10 * 1024 * 1024;

const FLAG_CHIP: Record<string, { label: string; tone: "bad" | "ok" | "neutral" | "warn" }> = {
  over_index: { label: "Above index", tone: "bad" },
  within_index: { label: "Within range", tone: "ok" },
  not_in_index: { label: "Not in the index", tone: "neutral" },
  unit_differs: { label: "Different unit", tone: "warn" },
  not_found_in_quote: { label: "Couldn’t confirm", tone: "warn" },
};

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).replace(/^data:[^,]*,/, ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function Results({ result, projectId }: { result: QuoteCheck; projectId: string }) {
  const lines = flaggedFirst(result.lines);
  const c = counts(result.lines);
  const above = overIndexTotal(result.lines);
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        <p className="flex flex-wrap items-center gap-2">
          <ToneChip label="AI check · advisory only" tone="info" size="small" />
          <ToneChip label={`Flagged · ${c.over}`} tone="bad" size="small" />
          <ToneChip label={`Within range · ${c.within}`} tone="ok" size="small" />
          <ToneChip label={`Not in index · ${c.notInIndex}`} tone="neutral" size="small" />
        </p>
        <Table caption="Checked lines, flagged first">
          <thead>
            <tr>
              <Th>Item</Th>
              <Th numeric>Quoted</Th>
              <Th numeric>Index</Th>
              <Th numeric>Diff.</Th>
              <Th>Flag</Th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => {
              const chip = FLAG_CHIP[l.flag] ?? { label: l.flag, tone: "neutral" as const };
              return (
                <Tr key={`${l.item}-${i}`}>
                  <Td>
                    <span className="block font-semibold">{l.item}</span>
                    <span className="type-small text-slate">
                      {l.quantity} {l.unit}
                    </span>
                  </Td>
                  <Td numeric>{formatMoney(l.unit_price_minor, "NGN")}</Td>
                  <Td numeric>
                    {l.index_price_minor != null ? formatMoney(l.index_price_minor, "NGN") : "–"}
                  </Td>
                  <Td numeric>
                    {l.percent_above_index != null
                      ? `${Number(l.percent_above_index) > 0 ? "+" : ""}${l.percent_above_index}%`
                      : "–"}
                  </Td>
                  <Td>
                    <ToneChip label={chip.label} tone={chip.tone} size="small" />
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
        <p className="type-small text-slate">
          AI read the lines; fixed rules decided the flags (more than {result.threshold_percent}% above the
          index). A flag isn&apos;t proof of anything — prices vary by brand and delivery.
        </p>
      </div>
      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Summary</CardLabel>
          <dl className="type-small flex flex-col gap-2">
            {[
              ["Lines checked", result.lines.length],
              [`Above index by more than ${result.threshold_percent}%`, c.over],
              ["Not in the index", c.notInIndex],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between gap-3">
                <dt className="text-slate">{k}</dt>
                <dd className="ibh-tabular font-semibold text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="flex justify-between gap-3 border-t border-line pt-3">
            <span className="text-slate">Above index, total</span>
            <span className="ibh-tabular font-semibold text-ink">{formatMoney(above, "NGN")}</span>
          </div>
          <p className="type-small text-slate">If the flagged lines were priced at the index.</p>
        </Card>
        <Card className="flex flex-col gap-2 p-5">
          <CardLabel>What you can do</CardLabel>
          <p className="type-small text-slate">Ask your contractor about these lines before you approve.</p>
          <Button asChild variant="outline">
            <Link href={`/projects/${projectId}/boq`}>Back to the BoQ</Link>
          </Button>
        </Card>
      </aside>
    </div>
  );
}

function PriceIndex() {
  const timeZone = useViewerTimeZone();
  const index = usePriceIndex();
  const id = useId();
  const [query, setQuery] = useState("");
  const items = (index.data ?? []).filter((p) => p.item.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <div className="flex flex-col gap-4">
      <p className="text-slate">
        Current prices from verified partner suppliers: the middle of each supplier&apos;s latest price. Items
        not updated recently are marked.
      </p>
      <label htmlFor={id} className="sr-only">
        Search materials
      </label>
      <input
        id={id}
        type="search"
        placeholder="Search materials"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="min-h-11 max-w-sm rounded-control border border-line-strong bg-white px-3 text-ink"
      />
      {index.isPending ? (
        <p className="text-slate">Loading the price index…</p>
      ) : !index.data ? (
        <Alert tone="bad" title="The price index couldn’t be loaded">
          Try again in a moment.
        </Alert>
      ) : !index.data.length ? (
        <p className="rounded-card bg-mist p-4 text-slate">
          No supplier prices yet. Prices appear here once partner suppliers report them.
        </p>
      ) : !items.length ? (
        <p className="text-slate">No material matches that search.</p>
      ) : (
        <Table caption="Enugu price index">
          <thead>
            <tr>
              <Th>Item</Th>
              <Th>Unit</Th>
              <Th numeric>Price</Th>
              <Th>Source</Th>
              <Th>Last updated</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <Tr key={p.item_key}>
                <Td className="font-semibold">{p.item}</Td>
                <Td>{p.unit}</Td>
                <Td numeric>{formatMoney(p.price_minor, p.currency)}</Td>
                <Td>
                  {p.supplier_count} {p.supplier_count === 1 ? "supplier" : "suppliers"}
                </Td>
                <Td>
                  {formatDate(p.last_observed_on, timeZone)}
                  {p.stale ? (
                    <ToneChip label="Out of date" tone="warn" size="small" className="ml-2" />
                  ) : null}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

export function QuoteChecker({ projectId }: { projectId: string }) {
  const ids = { file: useId() };
  const boq = useBoq(projectId);
  const check = useQuoteCheck();
  const [view, setView] = useState<"check" | "index">("check");
  const [source, setSource] = useState<"boq" | "pdf">("boq");
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const hasBoq = Boolean(boq.data?.milestones.length);
  const lineCount = boq.data?.milestones.reduce((n, m) => n + m.items.length, 0) ?? 0;

  const run = async () => {
    setProblem(null);
    if (source === "boq") {
      if (!boq.data || !hasBoq) return setProblem("There is no submitted BoQ to check yet.");
      check.mutate({ text: boqAsQuoteText(boq.data.milestones) });
      return;
    }
    if (!file) return setProblem("Choose a PDF first.");
    if (file.size > MAX_PDF_BYTES) return setProblem("That PDF is over 10 MB. Choose a smaller one.");
    check.mutate({ pdf_base64: await toBase64(file) });
  };

  const failure = check.error
    ? check.error instanceof ApiError && check.error.status === 422
      ? "We couldn’t read prices from that quote. Try the submitted BoQ, or a clearer PDF."
      : "The check didn’t finish. Nothing was saved. Try again."
    : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-6 sm:px-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="type-h1 flex items-center gap-2 text-ink">
          <Sparkles aria-hidden strokeWidth={1.75} className="size-6" />
          Check a quote against Enugu prices
        </h2>
        <SegmentedControl
          label="View"
          value={view}
          onChange={setView}
          segments={[
            { value: "check", label: "Quote check" },
            { value: "index", label: "Price index" },
          ]}
        />
      </div>
      {view === "index" ? (
        <PriceIndex />
      ) : check.data ? (
        <>
          <Results result={check.data} projectId={projectId} />
          <Button variant="outline" className="self-start" onClick={() => check.reset()}>
            Check something else
          </Button>
        </>
      ) : check.isPending ? (
        <Card role="status" className="flex items-center gap-3 p-6">
          <Loader2 aria-hidden strokeWidth={1.75} className="size-5 animate-spin text-accent" />
          <span className="text-ink">Checking… Usually under a minute.</span>
        </Card>
      ) : (
        <Card className="flex max-w-3xl flex-col gap-4 p-6">
          <p className="text-slate">
            We compare each unit price with what partner suppliers in Enugu charge this month.
          </p>
          <fieldset className="flex flex-col gap-3">
            <legend className="sr-only">What to check</legend>
            <label
              className={cn(
                "flex items-start gap-3 rounded-card border p-4",
                source === "boq" ? "border-2 border-navy-900" : "border-line-strong",
                !hasBoq && "text-muted",
              )}
            >
              <input
                type="radio"
                name="source"
                className="mt-1"
                checked={source === "boq"}
                disabled={!hasBoq}
                onChange={() => setSource("boq")}
              />
              <span>
                <span className="flex items-center gap-2 font-semibold text-ink">
                  The submitted BoQ{" "}
                  {hasBoq ? <ToneChip label="Recommended" tone="info" size="small" /> : null}
                </span>
                <span className="type-small text-slate">
                  {hasBoq
                    ? `${lineCount} lines · ${formatMoney(boq.data!.boq_total_minor, "NGN")}. Already priced line by line.`
                    : "Your contractor hasn't submitted the BoQ yet."}
                </span>
              </span>
            </label>
            <label
              className={cn(
                "flex items-start gap-3 rounded-card border p-4",
                source === "pdf" ? "border-2 border-navy-900" : "border-line-strong",
              )}
            >
              <input
                type="radio"
                name="source"
                className="mt-1"
                checked={source === "pdf"}
                onChange={() => setSource("pdf")}
              />
              <span className="flex flex-col gap-2">
                <span className="font-semibold text-ink">A quote PDF</span>
                <span className="type-small text-slate">
                  A quote your contractor sent you outside iBackHome. AI reads it into lines first.
                </span>
              </span>
            </label>
            {source === "pdf" ? (
              <div className="flex flex-col gap-1 pl-4">
                <label htmlFor={ids.file} className="type-small font-semibold text-ink">
                  Choose a PDF · up to 10 MB
                </label>
                <input
                  id={ids.file}
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="type-small"
                />
                {file ? (
                  <span className="type-small flex items-center gap-1 text-slate">
                    <FileText aria-hidden strokeWidth={1.75} className="size-4" /> {file.name}
                  </span>
                ) : null}
              </div>
            ) : null}
          </fieldset>
          {problem ? (
            <Alert tone="warn" title={problem} />
          ) : failure ? (
            <Alert tone="bad" title={failure} />
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setView("index")}
              className="type-small rounded-control font-semibold text-accent underline"
            >
              See the price index
            </button>
            <Button size="lg" onClick={() => void run()}>
              Run the check
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
