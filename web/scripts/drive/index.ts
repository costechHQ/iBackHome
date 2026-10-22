// Dev seed driver (local Docker Compose only): puts a milestone into the state you need, through the real API,
// as the seeded people. Run from web/ after backend/scripts/seed.py and simulator.py (see web/README.md):
//
//   bun scripts/drive/index.ts --to verified                  # next pending milestone of the first project
//   bun scripts/drive/index.ts --to disputed --project "3-bedroom bungalow, Trans-Ekulu"
//   bun scripts/drive/index.ts --to claimed --milestone 2     # a milestone by its sequence number
//   bun scripts/drive/index.ts --to funded --currency USD     # the client pays in USD (default GBP)
//   bun scripts/drive/index.ts --new-project --to funded      # a fresh active project (the gate test uses this)
//
// States: funded, claimed, verified, approved (release requested), released (waits for escrow), disputed,
// sent-back (the supervisor rejects the claim with reasons: back to funded, rework needed).
// --project takes a title or an id. Prints the milestone's id and client URL. Never touches the database; every step is an API call.
import { randomUUID } from "node:crypto";
import { parseArgs } from "node:util";

import { capture, waitAccepted } from "./capture";
import { DriveError } from "./env";
import { fundMilestone } from "./funding";
import { newProject } from "./project";
import { apiAs, ok, PEOPLE, type Person } from "./session";

const ORDER = ["pending", "funded", "claimed", "verified", "approved", "released"] as const;
type Target = (typeof ORDER)[number] | "disputed" | "sent-back";
const TARGETS: readonly Target[] = [
  "funded",
  "claimed",
  "verified",
  "approved",
  "released",
  "disputed",
  "sent-back",
];

const { values } = parseArgs({
  options: {
    to: { type: "string" },
    project: { type: "string" },
    "new-project": { type: "boolean", default: false },
    milestone: { type: "string" },
    photos: { type: "string", default: "2" },
    // The client picks the payment currency at checkout (GBP, USD or EUR); the BoQ itself is priced in NGN.
    currency: { type: "string", default: "GBP" },
  },
});

const step = (message: string) => console.log(`  - ${message}`);

async function main() {
  const target = values.to as Target | undefined;
  if (!target || !TARGETS.includes(target)) {
    throw new DriveError(`--to must be one of: ${TARGETS.join(", ")}`);
  }
  const client = await apiAs(PEOPLE.client);
  let projectRef = values.project;
  if (values["new-project"]) {
    const created = await newProject();
    projectRef = created.id;
    step(`new project "${created.title}": BoQ approved by all three, supervisor assigned`);
  }
  // An id is read directly (gate runs add projects, so it may be past the first page); a title is looked up.
  const isId = projectRef !== undefined && /^[0-9a-f-]{36}$/i.test(projectRef);
  let projectId = isId ? projectRef : undefined;
  if (!projectId) {
    const projects = ok(
      "projects",
      await client.GET("/api/v1/projects", { params: { query: { limit: 100 } } }),
    );
    projectId = (
      projectRef
        ? projects.items.find((p) => p.title === projectRef)
        : projects.items.find((p) => p.status === "active")
    )?.id;
  }
  if (!projectId)
    throw new DriveError("no active project: run backend/scripts/seed.py and simulator.py first");
  const project = ok(
    "project",
    await client.GET("/api/v1/projects/{project_id}", { params: { path: { project_id: projectId } } }),
  );

  const list = async () =>
    ok(
      "milestones",
      await client.GET("/api/v1/projects/{project_id}/milestones", {
        params: { path: { project_id: project.id } },
      }),
    );
  const milestones = await list();
  const want = target === "disputed" ? "verified" : target === "sent-back" ? "claimed" : target;
  const milestone = values.milestone
    ? milestones.find((m) => m.sequence === Number(values.milestone))
    : milestones.find((m) => m.status === "pending");
  if (!milestone) throw new DriveError("no milestone to drive (all funded? pass --milestone N)");
  console.log(
    `${project.title} · milestone ${milestone.sequence} "${milestone.name}" (${milestone.status}) -> ${target}`,
  );

  const supervisor = await assignedSupervisor(project.supervisor_id);
  const at = () => ORDER.indexOf(milestone.status as (typeof ORDER)[number]);
  const reach = (state: (typeof ORDER)[number]) =>
    ORDER.indexOf(state) <= ORDER.indexOf(want as (typeof ORDER)[number]);

  if (milestone.status === "pending" && reach("funded")) {
    await fundMilestone({
      projectId: project.id,
      milestoneId: milestone.id,
      clientId: project.client_id,
      currency: values.currency ?? "GBP",
      amountNgnMinor: milestone.amount_minor,
    });
    milestone.status = "funded";
    step("funded (signed Stripe webhook)");
  }

  let evidenceIds: string[] = [];
  if (milestone.status === "funded" && reach("claimed")) {
    const count = Number(values.photos);
    for (let i = 0; i < count; i++) evidenceIds.push(await capture(supervisor, project, milestone.id));
    await waitAccepted(supervisor, project.id, evidenceIds);
    step(`${count} signed supervisor photos accepted`);
    const contractor = await apiAs(PEOPLE.contractor);
    ok(
      "claim",
      await contractor.POST("/api/v1/milestones/{milestone_id}/claim", {
        params: { path: { milestone_id: milestone.id } },
        headers: { "Idempotency-Key": randomUUID() },
      }),
    );
    milestone.status = "claimed";
    step("claimed by the contractor");
  }

  if (target === "sent-back" && milestone.status === "claimed") {
    const ids = evidenceIds.length ? evidenceIds : [await capture(supervisor, project, milestone.id)];
    if (!evidenceIds.length) await waitAccepted(supervisor, project.id, ids);
    const api = await apiAs(supervisor);
    ok(
      "send back",
      await api.POST("/api/v1/milestones/{milestone_id}/verify", {
        params: { path: { milestone_id: milestone.id } },
        body: {
          decision: "rejected",
          checklist: [
            { item: "Driver check: finished as in the BoQ", passed: true, evidence_ids: [ids[0]!] },
            { item: "Driver check: no cracks on the north side", passed: false, evidence_ids: [ids.at(-1)!] },
          ],
          notes: "Sent back by the dev seed driver: fix the cracks on the north side, then claim again.",
        },
        headers: { "Idempotency-Key": randomUUID() },
      }),
    );
    milestone.status = "funded";
    step("sent back by the supervisor (rework)");
  }

  if (milestone.status === "claimed" && reach("verified")) {
    if (!evidenceIds.length) {
      evidenceIds = [await capture(supervisor, project, milestone.id)];
      await waitAccepted(supervisor, project.id, evidenceIds);
    }
    const api = await apiAs(supervisor);
    ok(
      "verify",
      await api.POST("/api/v1/milestones/{milestone_id}/verify", {
        params: { path: { milestone_id: milestone.id } },
        body: {
          decision: "verified",
          checklist: evidenceIds.map((id, i) => ({
            item: `Driver check ${i + 1}`,
            passed: true,
            evidence_ids: [id],
          })),
          notes: "Checked on site by the dev seed driver.",
        },
        headers: { "Idempotency-Key": randomUUID() },
      }),
    );
    milestone.status = "verified";
    step("verified by the supervisor");
  }

  if (target === "disputed" && milestone.status === "verified") {
    ok(
      "dispute",
      await client.POST("/api/v1/milestones/{milestone_id}/disputes", {
        params: { path: { milestone_id: milestone.id } },
        body: { reason: "Raised by the dev seed driver: the work doesn't match the BoQ." },
        headers: { "Idempotency-Key": randomUUID() },
      }),
    );
    milestone.status = "disputed";
    step("disputed by the client");
  }

  if (milestone.status === "verified" && reach("approved")) {
    ok(
      "approve",
      await client.POST("/api/v1/milestones/{milestone_id}/approve", {
        params: { path: { milestone_id: milestone.id } },
        headers: { "Idempotency-Key": randomUUID() },
      }),
    );
    milestone.status = "approved";
    step("approved by the client (release requested)");
  }

  if (target === "released") {
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      const now = (await list()).find((m) => m.id === milestone.id);
      if (now?.status === "released") {
        milestone.status = "released";
        break;
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
    step(
      milestone.status === "released"
        ? "released by the escrow partner"
        : "release not confirmed within 60 s",
    );
  }

  if (at() < 0 && milestone.status !== "disputed")
    throw new DriveError(`unexpected status ${milestone.status}`);
  console.log(`done: ${milestone.status}`);
  console.log(`  milestone ${milestone.id}`);
  console.log(`  client    /projects/${project.id}/milestones/${milestone.id}`);
}

/** The project's assigned supervisor among the seeded ones (the project names them by id only). */
async function assignedSupervisor(id: string | null): Promise<Person> {
  for (const person of [PEOPLE.supervisor, PEOPLE.supervisor_2]) {
    const me = ok("me", await (await apiAs(person)).GET("/api/v1/me"));
    if (me.id === id) return person;
  }
  throw new DriveError("the project's supervisor isn't one of the seeded supervisors");
}

main().catch((error: unknown) => {
  console.error(error instanceof DriveError ? `drive: ${error.message}` : error);
  process.exit(1);
});
