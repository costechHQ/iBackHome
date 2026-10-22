// A fresh active project for the gate test, made through the real API as the seeded people: the client creates
// it and sets the site, the contractor puts up a three-milestone BoQ, the client, contractor and ops approve it
// (which makes the project active and creates its milestones), and ops assigns a supervisor.
// Dev data only: a made-up site in Enugu, a few square metres apart each run.
import { randomUUID } from "node:crypto";

import { ok, apiAs, PEOPLE, type Person } from "./session";

const MILESTONES = [
  { name: "Foundation", price: 1_250_000_00 },
  { name: "Blockwork to lintel", price: 1_500_000_00 },
  { name: "Roofing", price: 1_750_000_00 },
];

function squareFence(lat: number, lon: number, half = 0.0004) {
  const [s, w, n, e] = [lat - half, lon - half, lat + half, lon + half];
  return {
    type: "Polygon",
    coordinates: [
      [
        [w, s],
        [e, s],
        [e, n],
        [w, n],
        [w, s],
      ],
    ],
  };
}

const key = () => ({ "Idempotency-Key": randomUUID() });

export async function newProject(
  supervisor: Person = PEOPLE.supervisor,
): Promise<{ id: string; title: string }> {
  const client = await apiAs(PEOPLE.client);
  const contractor = await apiAs(PEOPLE.contractor);
  const ops = await apiAs(PEOPLE.ops);

  const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");
  const title = `Gate test house ${stamp} ${randomUUID().slice(0, 4)}`;
  const project = ok(
    "create project",
    await client.POST("/api/v1/projects", {
      body: {
        title,
        address: "Dev site, Enugu",
        currency: "NGN",
        budget_minor: MILESTONES.reduce((sum, m) => sum + m.price, 0),
        contractor_phone: PEOPLE.contractor.identifier,
      },
      headers: key(),
    }),
  );

  // Somewhere around Enugu, away from the seeded sites.
  const lat = 6.43 + Math.random() * 0.02;
  const lon = 7.48 + Math.random() * 0.02;
  ok(
    "set site",
    await client.PUT("/api/v1/projects/{project_id}/site", {
      params: { path: { project_id: project.id } },
      body: { location: { lat, lon }, geofence: squareFence(lat, lon) },
      headers: key(),
    }),
  );

  ok(
    "submit BoQ",
    await contractor.PUT("/api/v1/projects/{project_id}/boq", {
      params: { path: { project_id: project.id } },
      body: {
        milestones: MILESTONES.map((m) => ({
          name: m.name,
          items: [
            {
              description: `${m.name}: labour and materials`,
              unit: "lot",
              quantity: 1,
              unit_price_minor: m.price,
            },
          ],
        })),
      },
      headers: key(),
    }),
  );

  for (const [who, api] of [
    ["client", client],
    ["contractor", contractor],
    ["ops", ops],
  ] as const) {
    ok(
      `BoQ approval (${who})`,
      await api.POST("/api/v1/projects/{project_id}/boq/approve", {
        params: { path: { project_id: project.id } },
        headers: key(),
      }),
    );
  }

  const supervisorId = ok("me", await (await apiAs(supervisor)).GET("/api/v1/me")).id;
  ok(
    "assign supervisor",
    await ops.POST("/api/v1/projects/{project_id}/supervisor", {
      params: { path: { project_id: project.id } },
      body: { supervisor_id: supervisorId },
      headers: key(),
    }),
  );
  return { id: project.id, title };
}
