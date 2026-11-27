// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MatchRequestDetail } from "./match-request-detail";

const get = vi.fn();
const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ GET: get, POST: post }),
}));
vi.mock("@/common/layout/ops-shell", () => ({
  OpsHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
}));

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";

function profile(id: string, name: string, over: Record<string, unknown> = {}) {
  return {
    id,
    user_id: `u-${id}`,
    business_name: name,
    contact_name: "Someone",
    summary: `${name} builds houses in Enugu.`,
    states_served: ["Enugu"],
    specialties: ["buildings"],
    years_in_business: 10,
    projects_completed: 20,
    vetting_status: "approved",
    listed: true,
    vetted_at: "2026-11-20T10:00:00Z",
    ...over,
  };
}
const DIRECTORY = [
  profile("p1", "Obi Works"),
  profile("p2", "Eze Builders"),
  profile("p3", "Okoro Roofing"),
  profile("p4", "Nwosu Ltd"),
];

function request(status: string, extra: Record<string, unknown> = {}) {
  return {
    id: "r1",
    project_id: PROJECT_ID,
    status,
    state: "Enugu",
    city: "Nsukka",
    work_type: "buildings",
    timeline: "Within three months",
    notes: "A flat plot.",
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

function serve(match: Record<string, unknown> | null) {
  get.mockImplementation(async (path: string) => {
    if (path === "/api/v1/projects/{project_id}") {
      return {
        data: { id: PROJECT_ID, title: "Bungalow", status: "draft" },
        response: new Response(null, { status: 200 }),
      };
    }
    if (path === "/api/v1/contractors") {
      return { data: { items: DIRECTORY, next_cursor: null }, response: new Response(null, { status: 200 }) };
    }
    if (match) return { data: match, response: new Response(null, { status: 200 }) };
    return {
      error: { error: { code: "match_request_not_found", message: "x" } },
      response: new Response(null, { status: 404 }),
    };
  });
  post.mockResolvedValue({ data: request("shortlisted"), response: new Response(null, { status: 200 }) });
}

function renderDetail() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MatchRequestDetail projectId={PROJECT_ID} environment="local" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});
afterEach(cleanup);

describe("MatchRequestDetail", () => {
  it("shows the brief and starts the directory on the request's state and kind of work", async () => {
    serve(request("open"));
    renderDetail();
    await screen.findByText("Nsukka, Enugu");
    expect(screen.getByText("A flat plot.")).toBeTruthy();
    await screen.findByText("Obi Works");
    const query = (
      get.mock.calls.find((c) => c[0] === "/api/v1/contractors")?.[1] as {
        params: { query: Record<string, unknown> };
      }
    ).params.query;
    expect(query).toMatchObject({ state: "Enugu", specialty: "buildings", listed: true });
  });

  it("keeps Send locked until a contractor is ticked, stops at three, and keeps the order", async () => {
    serve(request("open"));
    renderDetail();
    await screen.findByText("Obi Works");
    const send = screen.getByRole("button", {
      name: "Send the shortlist to the client",
    }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);

    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Put Eze Builders forward"));
    await user.click(screen.getByLabelText("Put Obi Works forward"));
    await user.click(screen.getByLabelText("Put Okoro Roofing forward"));
    expect(send.disabled).toBe(false);
    expect((screen.getByLabelText("Put Nwosu Ltd forward") as HTMLInputElement).disabled).toBe(true); // the fourth

    await user.click(screen.getByRole("button", { name: "Move Obi Works up" }));
    const order = screen.getAllByText(/^\d\. /).map((n) => n.textContent);
    expect(order).toEqual(["1. Obi Works", "2. Eze Builders", "3. Okoro Roofing"]);
  });

  it("sends the shortlist in order with the note, after a confirmation", async () => {
    serve(request("open"));
    renderDetail();
    await screen.findByText("Obi Works");
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Put Eze Builders forward"));
    await user.click(screen.getByLabelText("Put Obi Works forward"));
    await user.type(screen.getByLabelText(/Your note/), "Both phoned on Friday.");
    await user.click(screen.getByRole("button", { name: "Send the shortlist to the client" }));
    expect(post).not.toHaveBeenCalled(); // asks first
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByText(/Eze Builders, Obi Works/)).toBeTruthy();
    await user.click(within(dialog).getByRole("button", { name: "Yes, send it" }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [path, init] = post.mock.calls[0] as [
      string,
      { body: Record<string, unknown>; headers: Record<string, string> },
    ];
    expect(path).toBe("/api/v1/match-requests/{request_id}/shortlist");
    expect(init.body).toEqual({ contractor_ids: ["p2", "p1"], note: "Both phoned on Friday." });
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
  });

  it("starts from the current shortlist and offers to replace it", async () => {
    const chosen = [profile("p2", "Eze Builders"), profile("p1", "Obi Works")].map((p) => ({
      id: p.id,
      business_name: p.business_name,
      summary: p.summary,
      states_served: p.states_served,
      specialties: p.specialties,
      years_in_business: p.years_in_business,
      projects_completed: p.projects_completed,
      vetted_by_ibackhome: true,
    }));
    serve(request("shortlisted", { shortlist: chosen }));
    renderDetail();
    await screen.findByText("What the client sees");
    expect(screen.getByRole("button", { name: "Replace the shortlist" })).toBeTruthy();
    expect(((await screen.findByLabelText("Put Eze Builders forward")) as HTMLInputElement).checked).toBe(
      true,
    );
  });

  it("explains a contractor who is no longer available", async () => {
    serve(request("open"));
    post.mockResolvedValue({
      error: { error: { code: "contractor_not_available", message: "x" } },
      response: new Response(null, { status: 422 }),
    });
    renderDetail();
    await screen.findByText("Obi Works");
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Put Obi Works forward"));
    await user.click(screen.getByRole("button", { name: "Send the shortlist to the client" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Yes, send it" }),
    );
    await screen.findByText(/no longer approved, listed and active/);
  });

  it("cancels with a reason after a confirmation", async () => {
    serve(request("open"));
    renderDetail();
    await screen.findByText("Nsukka, Enugu");
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Reason (optional)"), "Client found one.");
    await user.click(screen.getByRole("button", { name: "Cancel the request" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancel the request" }),
    );
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]?.[0]).toBe("/api/v1/match-requests/{request_id}/cancel");
    expect((post.mock.calls[0]?.[1] as { body: unknown }).body).toEqual({ reason: "Client found one." });
  });

  it("shows a matched request read-only", async () => {
    const card = {
      id: "p1",
      business_name: "Obi Works",
      summary: "x",
      states_served: ["Enugu"],
      specialties: ["buildings"],
      years_in_business: 10,
      projects_completed: 20,
      vetted_by_ibackhome: true,
    };
    serve(request("matched", { shortlist: [card], chosen: card, decided_at: "2026-11-28T09:00:00Z" }));
    renderDetail();
    await screen.findByText("What the client chose from");
    expect(screen.getByText(/The client chose Obi Works/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /shortlist/i })).toBeNull();
    expect(screen.queryByLabelText("Put Obi Works forward")).toBeNull();
  });
});
