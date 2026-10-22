import { redirect } from "next/navigation";

// Until the ops overview (WEB-OPS-002) exists, the console opens on the dispute queue.
export default function OpsHome() {
  redirect("/ops/disputes");
}
