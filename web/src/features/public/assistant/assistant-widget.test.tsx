// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AssistantWidget } from "./assistant-widget";

const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ POST: post }),
}));

function answer(over: Record<string, unknown> = {}) {
  return {
    data: {
      answer: "Supervision is a monthly fee per project: Basic $100 a month.",
      related: [{ question: "What is the fee when I fund a milestone?" }],
      handoff: false,
      source: "faq",
      ...over,
    },
    response: new Response(null, { status: 200 }),
  };
}
const refused = (status: number, headers: Record<string, string> = {}) => ({
  error: { error: { code: "x", message: "backend text" } },
  response: new Response(null, { status, headers }),
});

async function open() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Ask a question" }));
  return user;
}

beforeEach(() => post.mockReset());
afterEach(cleanup);

describe("AssistantWidget", () => {
  it("is a closed round button until someone opens it", () => {
    render(<AssistantWidget />);
    expect(screen.getByRole("button", { name: "Ask a question" })).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens with the disclaimer, the suggestions and the box focused, and says it is automated", async () => {
    render(<AssistantWidget />);
    await open();
    const dialog = screen.getByRole("dialog", { name: "Ask iBackHome" });
    expect(dialog.textContent).toContain("Automated assistant");
    expect(dialog.textContent).toMatch(/Please don’t share passwords, your NIN or bank details/);
    expect(screen.getAllByRole("button", { name: /^(How|Can)/ })).toHaveLength(4);
    expect(document.activeElement).toBe(screen.getByLabelText("Your question"));
  });

  it("sends a typed question and shows the answer with related questions", async () => {
    post.mockResolvedValue(answer());
    render(<AssistantWidget />);
    const user = await open();
    await user.type(screen.getByLabelText("Your question"), "how much does it cost");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText(/Supervision is a monthly fee/);
    expect(post).toHaveBeenCalledTimes(1);
    const [path, init] = post.mock.calls[0] as [string, { body: unknown; signal: AbortSignal }];
    expect(path).toBe("/api/v1/assistant/chat");
    expect(init.body).toEqual({ message: "how much does it cost" });
    expect(init.signal).toBeInstanceOf(AbortSignal); // a slow answer is cut off after 15 seconds
    expect(screen.getByText("how much does it cost")).toBeTruthy(); // the visitor's own message
    expect(screen.getByRole("button", { name: "What is the fee when I fund a milestone?" })).toBeTruthy();
    expect(screen.queryByText("Try asking")).toBeNull(); // the suggestions go once there is a conversation
  });

  it("sends a suggestion on one tap, and a related question the same way", async () => {
    post.mockResolvedValue(answer());
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    await screen.findByText(/Supervision is a monthly fee/);
    await user.click(screen.getByRole("button", { name: "What is the fee when I fund a milestone?" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect((post.mock.calls[1]?.[1] as { body: { message: string } }).body.message).toBe(
      "What is the fee when I fund a milestone?",
    );
  });

  it("does not send an empty or one-letter question", async () => {
    render(<AssistantWidget />);
    const user = await open();
    const send = screen.getByRole("button", { name: "Send" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await user.type(screen.getByLabelText("Your question"), "a");
    expect(send.disabled).toBe(true);
    expect(post).not.toHaveBeenCalled();
  });

  it("shows contact buttons when the answer hands off to a person", async () => {
    post.mockResolvedValue(
      answer({
        answer: "I can’t see anyone’s account. Please call us.",
        related: [],
        handoff: true,
        source: "none",
      }),
    );
    render(<AssistantWidget />);
    const user = await open();
    await user.type(screen.getByLabelText("Your question"), "where is my money");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(/can’t see anyone’s account/);
    const group = screen.getAllByLabelText("Talk to a person")[0]!;
    expect(group.textContent).toContain("WhatsApp us");
    expect(group.querySelector('a[href^="https://wa.me/"]')).toBeTruthy();
    expect(group.querySelector('a[href^="mailto:"]')).toBeTruthy();
    expect(group.querySelector('a[href="/contact"]')).toBeTruthy();
  });

  it("explains when the assistant is off or busy, and offers a person", async () => {
    post.mockResolvedValue(refused(503));
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("isn’t available");
    expect(alert.textContent).not.toContain("backend text");
    expect(screen.getAllByLabelText("Talk to a person").length).toBeGreaterThan(0);
  });

  it("says how long to wait when rate limited", async () => {
    post.mockResolvedValue(refused(429, { "retry-after": "600" }));
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    await screen.findByText(/in about 10 minutes/);
  });

  it("closes with Escape or the close button and puts focus back on the round button", async () => {
    render(<AssistantWidget />);
    const user = await open();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Ask a question" }));

    await user.click(screen.getByRole("button", { name: "Ask a question" }));
    await user.click(screen.getByRole("button", { name: "Close the chat" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keeps the conversation while the panel is closed and opened again", async () => {
    post.mockResolvedValue(answer());
    render(<AssistantWidget />);
    let user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    await screen.findByText(/Supervision is a monthly fee/);
    await user.click(screen.getByRole("button", { name: "Close the chat" }));
    user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Ask a question" }));
    expect(screen.getByText(/Supervision is a monthly fee/)).toBeTruthy();
  });

  it("blocks a second question while one is being answered", async () => {
    let finish: (value: unknown) => void = () => {};
    post.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    expect(screen.getByText("Looking that up…")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Send" })); // empty: ignored
    expect(post).toHaveBeenCalledTimes(1);
    finish(answer());
    await screen.findByText(/Supervision is a monthly fee/);
    expect(screen.queryByText("Looking that up…")).toBeNull();
  });

  it("answers a question asked before from memory, with no second trip to the server", async () => {
    post.mockResolvedValue(answer());
    render(<AssistantWidget />);
    const user = await open();
    await user.type(screen.getByLabelText("Your question"), "how much does it cost");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText(/Supervision is a monthly fee/);
    expect(post).toHaveBeenCalledTimes(1);

    await user.type(screen.getByLabelText("Your question"), "  HOW MUCH does it   cost ");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(screen.getAllByText(/Supervision is a monthly fee/)).toHaveLength(2));
    expect(post).toHaveBeenCalledTimes(1); // the same question in other words/case: no new request
    expect(screen.queryByText("Looking that up…")).toBeNull();
  });

  it("keeps the keyboard ready after a typed question but not after a tapped suggestion", async () => {
    post.mockResolvedValue(answer());
    render(<AssistantWidget />);
    const user = await open();
    const box = screen.getByLabelText("Your question");
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    await screen.findByText(/Supervision is a monthly fee/);
    expect(document.activeElement).not.toBe(box); // a tap leaves the answer in view

    await user.type(box, "who holds my money");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(document.activeElement).toBe(box)); // typing: ready for the next one
  });

  it("gives up on a slow answer and offers Try again, which asks the same question", async () => {
    const timeout = new DOMException("The operation timed out.", "TimeoutError");
    post.mockRejectedValueOnce(timeout).mockResolvedValueOnce(answer());
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("taking too long");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByText(/Supervision is a monthly fee/);
    expect(post).toHaveBeenCalledTimes(2);
    expect((post.mock.calls[1]?.[1] as { body: { message: string } }).body.message).toBe(
      "How much does it cost?",
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does not offer Try again when asking again would only be refused", async () => {
    post.mockResolvedValue(refused(429, { "retry-after": "60" }));
    render(<AssistantWidget />);
    const user = await open();
    await user.click(screen.getByRole("button", { name: "How much does it cost?" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("sizes itself to the screen: the full height on a phone, a bounded panel from tablet up", async () => {
    render(<AssistantWidget />);
    await open();
    const panel = screen.getByRole("dialog");
    for (const cls of ["h-dvh", "sm:h-144", "sm:max-h-9/10", "sm:w-96", "md:w-104", "ibh-chat-panel"]) {
      expect(panel.className).toContain(cls);
    }
    // Comfortable touch targets: every suggestion and the close button are at least 44px.
    for (const button of screen.getAllByRole("button", { name: /^(How|Can)/ })) {
      expect(button.className).toContain("min-h-11");
    }
    expect(screen.getByRole("button", { name: "Close the chat" }).className).toContain("size-11");
    expect(screen.getByLabelText("Your question").className).toContain("text-base"); // 16px: no iOS zoom
  });
});
