// A new supervisor application waiting for ops (the vetting stack test): a fresh supervisor account and its
// application, made inside the api container with the backend's own supervision service, the way
// backend/scripts/seed.py makes the seeded supervisors. Nobody can become a supervisor through the API (new
// accounts are clients), so this is the one driver step that isn't an API call. Dev data only.
// The applicant declares the seeded contractor as a cousin, so once approved they are blocked from that
// contractor's projects.
import { execFileSync } from "node:child_process";

import { DriveError, REPO_ROOT } from "./env";
import { PEOPLE } from "./session";

const PYTHON = `
import asyncio, secrets
from app.base.users.models import User
from app.core.db import SessionLocal
from app.features.supervision import service
from app.features.supervision.schemas import DeclaredRelation, SupervisorApplication

async def main():
    n = secrets.randbelow(10**7)
    async with SessionLocal() as session:
        user = User(phone=f"+234809{n:07d}", role="supervisor", status="active",
                    full_name=f"Test Applicant {n:07d}", country="NG", timezone="Africa/Lagos")
        session.add(user)
        await session.flush()
        await service.submit_application(session, user.id, SupervisorApplication(
            registration_body="COREN", registration_no=f"R.{n:07d}",
            guarantor_1="Ngozi Eze, +2348031234567", guarantor_2="Emeka Obi, +2348039876543",
            related_contractors=[DeclaredRelation(contractor_phone="${PEOPLE.contractor.identifier}", relationship="cousin")]))
        await session.commit()
        print(f"applicant {user.id}")

asyncio.run(main())
`;

/** Creates the application and returns the new supervisor's user id. */
export function newApplicant(): string {
  const out = execFileSync("docker", ["compose", "exec", "-T", "api", "python", "-c", PYTHON], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  const id = /applicant ([0-9a-f-]{36})/.exec(out)?.[1];
  if (!id) throw new DriveError(`no applicant created:\n${out}`);
  return id;
}
