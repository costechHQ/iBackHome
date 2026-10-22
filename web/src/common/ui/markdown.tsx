import { Fragment, type ReactNode } from "react";

// A small, safe Markdown renderer (text only, never HTML): headings (#, ##, ###), paragraphs, "- " lists, pipe
// tables and **bold**. Used for the AI weekly reports and the legal pages (privacy policy, terms).

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold text-ink">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

const cells = (row: string) =>
  row
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((c) => c.trim());

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i]!.trimEnd();
    if (!line.trim()) {
      i++;
      continue;
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1]!.length;
      const Tag = level === 1 ? "h2" : level === 2 ? "h3" : "h4";
      blocks.push(
        <Tag key={i} className={level === 1 ? "type-h2 text-ink" : "type-h3 text-ink"}>
          {inline(heading[2]!)}
        </Tag>,
      );
      i++;
      continue;
    }
    if (line.trim().startsWith("|")) {
      const rows: string[] = [];
      while (i < lines.length && lines[i]!.trim().startsWith("|")) rows.push(lines[i++]!);
      // The separator row ("|---|:--|") only marks the header.
      const [head, ...rest] = rows.filter((r) => !/^[\s|:-]+$/.test(r));
      if (head) {
        blocks.push(
          <div key={i} className="overflow-x-auto rounded-card border border-line">
            <table className="type-small w-full border-collapse text-left">
              <thead>
                <tr>
                  {cells(head).map((c, j) => (
                    <th key={j} scope="col" className="border-b border-line px-3 py-2 font-semibold text-ink">
                      {inline(c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rest.map((r, k) => (
                  <tr key={k} className="border-b border-line last:border-b-0">
                    {cells(r).map((c, j) => (
                      <td key={j} className="px-3 py-2 text-ink">
                        {inline(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
      }
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i]!))
        items.push(lines[i++]!.replace(/^\s*[-*]\s+/, ""));
      blocks.push(
        <ul key={i} className="flex list-disc flex-col gap-1 pl-5 text-ink">
          {items.map((t, k) => (
            <li key={k}>{inline(t)}</li>
          ))}
        </ul>,
      );
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i]!.trim() && !/^(#{1,3}\s|\s*[-*]\s|\s*\|)/.test(lines[i]!))
      para.push(lines[i++]!.trim());
    blocks.push(
      <p key={i} className="text-ink">
        {inline(para.join(" "))}
      </p>,
    );
  }
  return <div className="flex flex-col gap-4">{blocks}</div>;
}

/** The first plain paragraph, for the list's one-line summary. */
export function summaryOf(source: string): string {
  const para = source
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .find((b) => b && !/^(#|\||[-*]\s)/.test(b));
  const text = (para ?? "").replace(/\*\*/g, "").replace(/\s+/g, " ");
  return text.length > 180 ? `${text.slice(0, 177)}…` : text;
}
