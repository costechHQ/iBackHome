// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Button } from "./button";
import { cn } from "./cn";
import { ConfirmDialog } from "./dialog";
import { ErrorSummary } from "./field";
import { MoneyInline } from "./money-display";
import { SegmentedControl } from "./segmented";
import { StatusChip } from "./status-chip";
import { initials } from "./surfaces";

afterEach(cleanup);

describe("cn", () => {
  it("lets a later class of the same kind win, our type styles included", () => {
    expect(cn("bg-white", "bg-primary")).toBe("bg-primary");
    expect(cn("type-body", "type-small")).toBe("type-small");
    expect(cn("type-small", "font-semibold")).toBe("type-small font-semibold");
  });
});

describe("Button", () => {
  it("blocks a second click while a write is in flight, without looking disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Approve release
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Approve release" });
    expect(button).toHaveProperty("disabled", false);
    expect(button.getAttribute("aria-disabled")).toBe("true");
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect(button.className).toContain("bg-primary");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders a link with button styles", () => {
    render(
      <Button asChild>
        <a href="/home">Go to my projects</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Go to my projects" });
    expect(link.getAttribute("href")).toBe("/home");
    expect(link.className).toContain("bg-primary");
  });
});

function DialogHarness({
  aboutMoney,
  onConfirm = () => {},
}: {
  aboutMoney?: boolean;
  onConfirm?: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open
      </button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Approve this order?"
        description="Paid from the milestone's escrow."
        confirmLabel="Approve order"
        onConfirm={onConfirm}
        aboutMoney={aboutMoney}
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("moves focus in, puts the safe choice first, and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    const trigger = screen.getByRole("button", { name: "Open" });
    await user.click(trigger);
    const dialog = screen.getByRole("alertdialog", { name: "Approve this order?" });
    expect(dialog.contains(document.activeElement)).toBe(true);
    const buttons = screen.getAllByRole("button").filter((b) => dialog.contains(b));
    expect(buttons.map((b) => b.textContent)).toEqual(["Cancel", "Approve order"]);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("ignores Escape when the dialog is about money", async () => {
    const user = userEvent.setup();
    render(<DialogHarness aboutMoney />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("alertdialog")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("keeps focus inside while tabbing", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    const dialog = screen.getByRole("alertdialog");
    for (let i = 0; i < 5; i++) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
  });
});

describe("SegmentedControl", () => {
  it("is one tab stop that arrow keys move through", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [value, setValue] = useState<"open" | "resolved">("open");
      return (
        <SegmentedControl
          label="Dispute status"
          value={value}
          onChange={setValue}
          segments={[
            { value: "open", label: "Open" },
            { value: "resolved", label: "Resolved" },
          ]}
        />
      );
    }
    render(<Harness />);
    await user.tab();
    expect(document.activeElement?.textContent).toBe("Open");
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "Resolved" }).getAttribute("aria-checked")).toBe("true");
    expect(document.activeElement?.textContent).toBe("Resolved");
  });
});

describe("ErrorSummary", () => {
  it("takes focus and links every problem to its field", () => {
    render(
      <ErrorSummary problems={[{ fieldId: "wa", message: "WhatsApp number is missing a country code" }]} />,
    );
    const alert = screen.getByRole("alert");
    expect(document.activeElement).toBe(alert);
    expect(screen.getByText("Fix 1 thing to continue")).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toBe("#wa");
  });
});

describe("money and status", () => {
  it("shows a client their currency, then NGN and the rate; others NGN only", () => {
    const { container, rerender } = render(
      <MoneyInline
        ngnMinor={1_326_000_000}
        client={{ amountMinor: 680_000, currency: "GBP" }}
        rate={{ fxRate: "1950.0000000000" }}
      />,
    );
    expect(container.textContent).toBe("£6,800.00 · ₦13,260,000 · £1 = ₦1,950.00");
    rerender(
      <MoneyInline
        ngnMinor={1_326_000_000}
        client={{ amountMinor: 680_051, currency: "GBP", estimate: true }}
      />,
    );
    expect(container.textContent).toBe("≈ £6,801 · ₦13,260,000");
    rerender(<MoneyInline ngnMinor={1_326_000_000} />);
    expect(container.textContent).toBe("₦13,260,000");
  });

  it("names the state in the chip, per viewer", () => {
    render(<StatusChip entity="evidence" state="flagged" audience="client" />);
    expect(screen.getByText("Under review by iBackHome")).toBeTruthy();
  });

  it("makes initials from a name", () => {
    expect(initials("Sample Client Name")).toBe("SN");
    expect(initials("Ops")).toBe("O");
    expect(initials(null)).toBe("?");
  });
});
