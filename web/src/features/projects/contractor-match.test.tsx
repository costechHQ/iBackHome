// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContractorMatch } from "./contractor-match";

const get = vi.fn();
const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ GET: get, POST: post }),
}));

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const CARD = {
  id: "c1",
  business_name: "Obi Building Works",
  summary: "Established Enugu builder with twelve years on residential buildings and roofing.",
  states_served: ["Enugu", "Anambra"],
  specialties: ["buildings", "roofing"],
  years_in_business: 12,
  projects_completed: 30,
  vetted_by_ibackhome: true,
};
const CARD_2 = {
  ...CARD,
  id: "c2",
  business_name: "Eze Builders",
  summary: "Roofing specialists in Anambra.",
};

function request(status: string, extra: Record<string, unknown> = {}) {
  return {
    id: "r1",
    project_id: PROJECT_ID,
    status,
    state: "Enugu",
    city: "Enugu",
    work_type: "buildings",
    timeline: "Within three months",
    notes: null,
    budget_minor: 30_000_000_00,
    currency: "NGN",
    created_at: "2026-11-27T10:00:00Z",
    decided_at: null,
    cancel_reason: null,
    shortlist: [],
    chosen: null,
    ...extra,
  };
}

function serve(opts: { project?: Record<string, unknown>; match?: Record<string, unknown> | null }) {
  const project = {
    id: PROJECT_ID,
    status: "draft",
    contractor_id: null,
    title: "Bungalow",
    ...opts.project,
  };
  get.mockImplementation(async (path: string) => {
    if (path === "/api/v1/projects/{project_id}") {
      return { data: project, response: new Response(null, { status: 200 }) };
    }
    if (opts.match) return { data: opts.match, response: new Response(null, { status: 200 }) };
    return {
      error: { error: { code: "match_request_not_found", message: "x" } },
      response: new Response(null, { status: 404 }),
    };
  });
  post.mockResolvedValue({ data: request("open"), response: new Response(null, { status: 201 }) });
}

function renderScreen() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ContractorMatch projectId={PROJECT_ID} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});
afterEach(cleanup);

describe("ContractorMatch", () => {
  it("shows the brief form when there is no request, and checks it before sending", async () => {
    serve({ match: null });
    renderScreen();
    await screen.findByRole("form", { name: "Contractor request" });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Ask for a contractor" }));
    expect(screen.getByText("Choose the state you are building in.")).toBeTruthy();
    expect(screen.getByText("Choose the kind of work.")).toBeTruthy();
    expect(post).not.toHaveBeenCalled();
  });

  it("sends the brief once with an Idempotency-Key and no budget", async () => {
    serve({ match: null });
    renderScreen();
    await screen.findByRole("form", { name: "Contractor request" });
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("State"), "Enugu");
    await user.type(screen.getByLabelText("City or town"), "Enugu");
    await user.selectOptions(screen.getByLabelText("Kind of work"), "buildings");
    await user.type(screen.getByLabelText("When do you want to start?"), "Within three months");
    await user.click(screen.getByRole("button", { name: "Ask for a contractor" }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [path, init] = post.mock.calls[0] as [
      string,
      { body: Record<string, unknown>; headers: Record<string, string> },
    ];
    expect(path).toBe("/api/v1/projects/{project_id}/match-request");
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
    expect(init.body).toEqual({
      state: "Enugu",
      city: "Enugu",
      work_type: "buildings",
      timeline: "Within three months",
      notes: null,
    });
  });

  it("says we are finding contractors while the request is open, and can cancel it", async () => {
    serve({ match: request("open") });
    renderScreen();
    await screen.findByText("We are finding contractors");
    expect(screen.getByText("Enugu, Enugu")).toBeTruthy();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Cancel this request" }));
    expect(post).not.toHaveBeenCalled(); // asks first
    await user.click(screen.getByRole("button", { name: "Cancel the request" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]?.[0]).toBe("/api/v1/match-requests/{request_id}/cancel");
  });

  it("shows the shortlist as cards with no contact details, and chooses after a confirmation", async () => {
    serve({ match: request("shortlisted", { shortlist: [CARD, CARD_2] }) });
    const { container } = renderScreen();
    await screen.findByText("Obi Building Works");
    expect(screen.getByText("Eze Builders")).toBeTruthy();
    expect(screen.getAllByText("Vetted by iBackHome")).toHaveLength(2);
    expect(container.textContent).not.toMatch(/\+234|@\w|0[789]\d{9}/); // no phone number or email

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Choose Eze Builders" }));
    expect(post).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Choose this contractor" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [path, init] = post.mock.calls[0] as [
      string,
      { body: { contractor_id: string }; headers: Record<string, string> },
    ];
    expect(path).toBe("/api/v1/match-requests/{request_id}/choose");
    expect(init.body).toEqual({ contractor_id: "c2" });
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("explains a refusal when the contractor is no longer available", async () => {
    serve({ match: request("shortlisted", { shortlist: [CARD] }) });
    post.mockResolvedValue({
      error: { error: { code: "contractor_not_available", message: "x" } },
      response: new Response(null, { status: 409 }),
    });
    renderScreen();
    await screen.findByText("Obi Building Works");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Choose Obi Building Works" }));
    await user.click(screen.getByRole("button", { name: "Choose this contractor" }));
    await screen.findByText(/no longer available/);
  });

  it("shows who was chosen once matched", async () => {
    serve({
      project: { contractor_id: "u1" },
      match: request("matched", { shortlist: [CARD], chosen: CARD, decided_at: "2026-11-28T09:00:00Z" }),
    });
    renderScreen();
    await screen.findByText("You chose Obi Building Works");
    expect(screen.getByText("Your contractor")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Choose/ })).toBeNull();
  });

  it("offers a new request after a cancelled one, and says the earlier was cancelled", async () => {
    serve({ match: request("cancelled", { cancel_reason: "Found one myself." }) });
    renderScreen();
    await screen.findByRole("form", { name: "Contractor request" });
    expect(screen.getByText(/earlier request was cancelled/)).toBeTruthy();
  });

  it("will not offer a request when the project already has a contractor or is past set-up", async () => {
    serve({ project: { contractor_id: "u1" }, match: null });
    renderScreen();
    await screen.findByText("Your project already has a contractor");
    cleanup();
    serve({ project: { status: "boq_review" }, match: null });
    renderScreen();
    await screen.findByText("This project is past set-up");
  });
});
