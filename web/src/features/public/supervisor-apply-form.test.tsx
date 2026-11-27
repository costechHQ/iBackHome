// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupervisorApplyForm } from "./supervisor-apply-form";

const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ POST: post }),
}));

const ok = () => ({ data: { id: "a1", status: "pending" }, response: new Response(null, { status: 201 }) });
const refused = (status: number, code: string, headers: Record<string, string> = {}) => ({
  error: { error: { code, message: "backend text" } },
  response: new Response(null, { status, headers }),
});

function renderForm() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <SupervisorApplyForm />
    </QueryClientProvider>,
  );
}

async function fillValid() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Full name"), "Ngozi Eze");
  await user.type(screen.getByLabelText("Phone number"), "08031234567");
  await user.type(screen.getByLabelText("Email"), "ngozi@example.com");
  await user.selectOptions(screen.getByLabelText("State"), "Enugu");
  await user.type(screen.getByLabelText("City or town"), "Enugu");
  await user.selectOptions(screen.getByLabelText("Registration body"), "COREN");
  await user.type(screen.getByLabelText("Registration number"), "R.98765");
  await user.type(screen.getByLabelText("Years of experience"), "8");
  await user.type(screen.getByLabelText("Guarantor 1: name"), "Emeka Obi");
  await user.type(screen.getByLabelText("Guarantor 1: phone"), "08051234567");
  await user.type(screen.getByLabelText("Guarantor 2: name"), "Ada Nwosu");
  await user.type(screen.getByLabelText("Guarantor 2: phone"), "08071234567");
  await user.click(screen.getByLabelText(/I agree that iBackHome may contact me/));
  return user;
}

// Filling a whole form field by field is slow when the full suite runs in parallel.
vi.setConfig({ testTimeout: 20_000 });

beforeEach(() => post.mockReset());
afterEach(cleanup);

describe("SupervisorApplyForm", () => {
  it("does not ask for a NIN anywhere", () => {
    renderForm();
    expect(screen.queryByLabelText(/\bNIN\b/i)).toBeNull();
    expect(screen.queryByLabelText(/national identification/i)).toBeNull();
    expect(screen.getByLabelText("Registration number")).toBeTruthy();
  });

  it("lists what is missing and sends nothing when the form is empty", async () => {
    renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Send my application" }));
    expect(screen.getByRole("alert").textContent).toContain("Fix 13 things to continue");
    expect(post).not.toHaveBeenCalled();
  });

  it("sends a complete form once, with an Idempotency-Key, and then confirms", async () => {
    post.mockResolvedValue(ok());
    renderForm();
    const user = await fillValid();
    await user.click(screen.getByRole("button", { name: "Send my application" }));

    await screen.findByText("Application received");
    expect(post).toHaveBeenCalledTimes(1);
    const [path, init] = post.mock.calls[0] as [
      string,
      { body: Record<string, unknown>; headers: Record<string, string> },
    ];
    expect(path).toBe("/api/v1/supervisor-applications");
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
    expect(init.body).toMatchObject({
      full_name: "Ngozi Eze",
      registration_body: "COREN",
      registration_no: "R.98765",
      years_experience: 8,
      consent: true,
      website: "",
      relatives: [],
    });
    expect(screen.getByText("ngozi@example.com")).toBeTruthy(); // the confirmation says where we will write
    expect(screen.queryByRole("button", { name: "Send my application" })).toBeNull();
  });

  it("sends what a bot typed into the hidden field", async () => {
    post.mockResolvedValue(ok());
    const { container } = renderForm();
    const user = await fillValid();
    const trap = container.querySelector<HTMLInputElement>('input[name="website"]');
    expect(trap?.tabIndex).toBe(-1);
    fireEvent.change(trap!, { target: { value: "http://spam.example" } });
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    expect((post.mock.calls[0]?.[1] as { body: { website: string } }).body.website).toBe(
      "http://spam.example",
    );
  });

  it("keeps the form and says so when we already have an application", async () => {
    post.mockResolvedValue(refused(409, "application_exists"));
    renderForm();
    const user = await fillValid();
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    await screen.findByText(/already have an application/);
    expect((screen.getByLabelText("Full name") as HTMLInputElement).value).toBe("Ngozi Eze"); // nothing lost
    expect(screen.queryByText("Application received")).toBeNull();
  });

  it("says how long to wait when rate limited", async () => {
    post.mockResolvedValue(refused(429, "rate_limited", { "retry-after": "600" }));
    renderForm();
    const user = await fillValid();
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    await screen.findByText(/in about 10 minutes/);
  });

  it("adds and removes relatives, up to three", async () => {
    renderForm();
    const user = userEvent.setup();
    const add = () => screen.getByRole("button", { name: "Add a relative" });
    await user.click(add());
    await user.click(add());
    await user.click(add());
    expect(screen.queryByRole("button", { name: "Add a relative" })).toBeNull();
    expect(screen.getAllByLabelText(/Relative \d: name/)).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "Remove relative 2" }));
    expect(screen.getAllByLabelText(/Relative \d: name/)).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Add a relative" })).toBeTruthy();
  });

  it("sends a filled relative and drops an empty row", async () => {
    post.mockResolvedValue(ok());
    renderForm();
    const user = await fillValid();
    await user.click(screen.getByRole("button", { name: "Add a relative" }));
    await user.type(screen.getByLabelText("Relative 1: name"), "Chidi Eze");
    await user.type(screen.getByLabelText("Relative 1: phone"), "08012345678");
    await user.click(screen.getByRole("button", { name: "Add a relative" }));
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    expect((post.mock.calls[0]?.[1] as { body: { relatives: unknown } }).body.relatives).toEqual([
      { name: "Chidi Eze", phone: "08012345678" },
    ]);
  });
});
