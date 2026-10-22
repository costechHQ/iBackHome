// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ReportMarkdown, summaryOf } from "./markdown";

const report = `# Weekly report

Roofing was **finished** and verified this week.

## Progress against the BoQ

| Milestone | Status |
|---|---|
| Foundation | Released |
| Roofing | Verified |

- Trusses up
- Fascia fixed

<script>alert(1)</script>`;

afterEach(cleanup);

describe("report Markdown", () => {
  it("renders headings, paragraphs, bold, tables and lists", () => {
    render(<ReportMarkdown source={report} />);
    expect(screen.getByRole("heading", { name: "Weekly report" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Progress against the BoQ" })).toBeTruthy();
    expect(screen.getByText("finished").tagName).toBe("STRONG");
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(within(table).getByRole("columnheader", { name: "Milestone" })).toBeTruthy();
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Trusses up",
      "Fascia fixed",
    ]);
  });

  it("never renders HTML from the report", () => {
    const { container } = render(<ReportMarkdown source={report} />);
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText("<script>alert(1)</script>")).toBeTruthy();
  });

  it("takes the first paragraph as the summary", () => {
    expect(summaryOf(report)).toBe("Roofing was finished and verified this week.");
    expect(summaryOf("x".repeat(300))).toHaveLength(178);
  });
});
