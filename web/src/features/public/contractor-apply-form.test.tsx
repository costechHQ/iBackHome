// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContractorApplyForm } from "./contractor-apply-form";

const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ POST: post }),
}));

const ok = () => ({ data: { id: "c1", status: "pending" }, response: new Response(null, { status: 201 }) });
const refused = (status: number, code: string, headers: Record<string, string> = {}) => ({
  error: { error: { code, message: "backend text" } },
  response: new Response(null, { status, headers }),
});

function renderForm() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <ContractorApplyForm />
    </QueryClientProvider>,
  );
}

async function fillValid() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Business name"), "Obi Building Works");
  await user.type(screen.getByLabelText("Contact person"), "Chinedu Obi");
  await user.type(screen.getByLabelText("Phone number"), "08031234567");
  await user.type(screen.getByLabelText("Email"), "obi@example.com");
  await user.type(screen.getByLabelText("Years in business"), "12");
  await user.type(screen.getByLabelText("Projects completed"), "30");
  await user.selectOptions(screen.getByLabelText("States you work in"), "Enugu");
  await user.selectOptions(screen.getByLabelText("States you work in"), "Anambra");
  await user.click(screen.getByLabelText("Buildings"));
  await user.click(screen.getByLabelText("Roofing"));
  await user.type(screen.getByLabelText("CAC RC number"), "RC1234567");
  await user.type(screen.getByLabelText("Reference 1: name"), "Emeka Obi");
  await user.type(screen.getByLabelText("Reference 1: phone"), "08051234567");
  await user.type(screen.getByLabelText("Reference 2: name"), "Ada Nwosu");
  await user.type(screen.getByLabelText("Reference 2: phone"), "08071234567");
  await user.click(screen.getByLabelText(/I agree that iBackHome may contact me/));
  return user;
}

beforeEach(() => post.mockReset());
afterEach(cleanup);

describe("ContractorApplyForm", () => {
  it("does not ask for a NIN anywhere", () => {
    renderForm();
    expect(screen.queryByLabelText(/\bNIN\b/i)).toBeNull();
    expect(screen.queryByLabelText(/national identification/i)).toBeNull();
    expect(screen.getByLabelText("CAC RC number")).toBeTruthy();
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
    expect(path).toBe("/api/v1/contractor-applications");
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
    expect(init.body).toMatchObject({
      business_name: "Obi Building Works",
      states_served: ["Enugu", "Anambra"],
      specialties: ["buildings", "roofing"],
      years_in_business: 12,
      projects_completed: 30,
      cac_rc_number: "RC1234567",
      corbon_number: null,
      consent: true,
      website: "",
    });
    expect(screen.getByText("obi@example.com")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Send my application" })).toBeNull();
  });

  it("adds and removes states, never offering one twice", async () => {
    renderForm();
    const user = userEvent.setup();
    const select = screen.getByLabelText("States you work in") as HTMLSelectElement;
    await user.selectOptions(select, "Enugu");
    await user.selectOptions(select, "Lagos");
    expect(screen.getByRole("button", { name: "Remove Enugu" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Remove Lagos" })).toBeTruthy();
    expect(Array.from(select.options).map((o) => o.value)).not.toContain("Enugu");
    await user.click(screen.getByRole("button", { name: "Remove Enugu" }));
    expect(screen.queryByRole("button", { name: "Remove Enugu" })).toBeNull();
    expect(Array.from(select.options).map((o) => o.value)).toContain("Enugu");
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
    expect((screen.getByLabelText("Business name") as HTMLInputElement).value).toBe("Obi Building Works");
    expect(screen.queryByText("Application received")).toBeNull();
  });

  it("says how long to wait when rate limited", async () => {
    post.mockResolvedValue(refused(429, "rate_limited", { "retry-after": "600" }));
    renderForm();
    const user = await fillValid();
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    await screen.findByText(/in about 10 minutes/);
  });
});
