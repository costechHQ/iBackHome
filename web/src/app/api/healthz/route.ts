// Liveness check for the container and Playwright: the Next server is up. It does not call the backend.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" }, { headers: { "Cache-Control": "no-store" } });
}
