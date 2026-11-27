// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContractorDetail } from "./contractor-detail";

const get = vi.fn();
const post = vi.fn();
vi.mock("@/common/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/common/api/client")>()),
  api: () => ({ GET: get, POST: post }),
}));
vi.mock("@/common/layout/ops-shell", () => ({
  OpsHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
}));

const APP = {
  id: "11111111-1111-1111-1111-111111111111",
  business_name: "Obi Building Works",
  contact_name: "Chinedu Obi",
  states_served: ["Enugu", "Anambra"],
  specialties: ["buildings", "roofing"],
  status: "pending",
  created_at: "2026-11-27T10:00:00Z",
  updated_at: "2026-11-27T10:00:00Z",
  phone: "+2348031234567",
  email: "obi@example.com",
  years_in_business: 12,
  projects_completed: 30,
  cac_rc_number: "RC1234567",
  corbon_number: null,
  reference_1_name: "Emeka Obi",
  reference_1_phone: "+2348051234567",
  reference_2_name: "Ada Nwosu",
  reference_2_phone: "+2348071234567",
  registration_verified: false,
  reference_1_verified: false,
  reference_2_verified: false,
  ops_notes: null,
  rejection_reason: null,
  decided_by: null,
  decided_at: null,
  consented_at: "2026-11-27T10:00:00Z",
};
const SUMMARY = "Established Enugu builder with twelve years on residential buildings and roofing.";

function respond(app: Record<string, unknown> = APP) {
  get.mockResolvedValue({ data: app, response: new Response(null, { status: 200 }) });
  post.mockResolvedValue({
    data: { ...app, status: "approved" },
    response: new Response(null, { status: 200 }),
  });
}

function renderDetail() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ContractorDetail applicationId={APP.id} environment="local" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});
afterEach(cleanup);

describe("ContractorDetail", () => {
  it("shows the application and keeps Approve locked until the checks and the summary are done", async () => {
    respond();
    renderDetail();
    await screen.findByText("Chinedu Obi");
    const approve = screen.getByRole("button", { name: "Approve contractor" }) as HTMLButtonElement;
    expect(approve.disabled).toBe(true);
    expect(screen.getByText(/Approve stays locked/)).toBeTruthy();

    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Registration checked on the register"));
    await user.click(screen.getByLabelText("First reference confirmed by phone"));
    await user.click(screen.getByLabelText("Second reference confirmed by phone"));
    expect(approve.disabled).toBe(true); // still no summary
    await user.type(screen.getByLabelText(/Profile summary/), SUMMARY);
    expect(approve.disabled).toBe(false);
    expect(screen.queryByText(/Approve stays locked/)).toBeNull();
  });

  it("asks for no registration check when the applicant gave no number", async () => {
    respond({ ...APP, cac_rc_number: null });
    renderDetail();
    await screen.findByText("Chinedu Obi");
    expect(screen.queryByLabelText("Registration checked on the register")).toBeNull();
    expect(screen.getByText(/nothing to check/)).toBeTruthy();
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("First reference confirmed by phone"));
    await user.click(screen.getByLabelText("Second reference confirmed by phone"));
    await user.type(screen.getByLabelText(/Profile summary/), SUMMARY);
    expect((screen.getByRole("button", { name: "Approve contractor" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("sends the approval with the ticks, the notes and the summary after a confirmation", async () => {
    respond();
    renderDetail();
    await screen.findByText("Chinedu Obi");
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Registration checked on the register"));
    await user.click(screen.getByLabelText("First reference confirmed by phone"));
    await user.click(screen.getByLabelText("Second reference confirmed by phone"));
    await user.type(screen.getByLabelText(/What you looked at/), "RC checked on the CAC register.");
    await user.type(screen.getByLabelText(/Profile summary/), SUMMARY);
    await user.click(screen.getByRole("button", { name: "Approve contractor" }));
    expect(post).not.toHaveBeenCalled(); // asks first
    await user.click(screen.getAllByRole("button", { name: "Approve contractor" }).at(-1)!); // the dialog's

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [path, init] = post.mock.calls[0] as [
      string,
      {
        body: Record<string, unknown>;
        headers: Record<string, string>;
        params: { path: { application_id: string } };
      },
    ];
    expect(path).toBe("/api/v1/contractor-applications/{application_id}/decision");
    expect(init.params.path.application_id).toBe(APP.id);
    expect(init.headers["Idempotency-Key"]).toBeTruthy();
    expect(init.body).toEqual({
      decision: "approved",
      registration_verified: true,
      reference_1_verified: true,
      reference_2_verified: true,
      notes: "RC checked on the CAC register.",
      summary: SUMMARY,
    });
  });

  it("will not reject without a reason, then sends it", async () => {
    respond();
    renderDetail();
    await screen.findByText("Chinedu Obi");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(screen.getByText("Say why, so the applicant knows what to fix.")).toBeTruthy();
    expect(post).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/Reason/), "We could not verify the RC number.");
    await user.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect((post.mock.calls[0]?.[1] as { body: Record<string, unknown> }).body).toMatchObject({
      decision: "rejected",
      reason: "We could not verify the RC number.",
    });
  });

  it("explains a phone number that belongs to another role", async () => {
    respond();
    post.mockResolvedValue({
      error: { error: { code: "role_conflict", message: "x" } },
      response: new Response(null, { status: 409 }),
    });
    renderDetail();
    await screen.findByText("Chinedu Obi");
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Registration checked on the register"));
    await user.click(screen.getByLabelText("First reference confirmed by phone"));
    await user.click(screen.getByLabelText("Second reference confirmed by phone"));
    await user.type(screen.getByLabelText(/Profile summary/), SUMMARY);
    await user.click(screen.getByRole("button", { name: "Approve contractor" }));
    await user.click(screen.getAllByRole("button", { name: "Approve contractor" }).at(-1)!);
    await screen.findByText(/already belongs to a client, supervisor, supplier or ops account/);
  });

  it("shows a decided application read-only", async () => {
    respond({
      ...APP,
      status: "rejected",
      rejection_reason: "No valid registration.",
      decided_at: "2026-11-28T09:00:00Z",
    });
    renderDetail();
    await screen.findByText(/No valid registration\./);
    expect(screen.queryByRole("button", { name: "Approve contractor" })).toBeNull();
    expect((screen.getByLabelText("First reference confirmed by phone") as HTMLInputElement).disabled).toBe(
      true,
    );
  });
});
