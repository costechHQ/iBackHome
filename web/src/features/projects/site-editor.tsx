"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, CircleAlert, LocateFixed, MapPin, Pentagon, Trash2, Undo2 } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useId, useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useProject } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { fromGeoJson, insidePolygon, metresBetween, toGeoJson, type LatLon } from "@/common/map/geo";
import type { MapMode } from "@/common/map/geofence-map";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

import { useSaveSite } from "./api";

// WEB-CLIENT-004 Site and boundary at /projects/:id/site: drag the pin, click to add boundary corners (three or
// more make the shape), undo, clear, save. The client can change it while the project is draft or in BoQ
// review; after approval it is locked (409 site_locked) and only ops can change it. The server decides
// inside/outside; the screen says it in words too. "Ask our team to change it" waits for a contact page (W-2).
// Keyboard users set the pin by its coordinates and a square boundary around it (PACKAGE-REPORT W-30).
// Ops use the same editor from the console (WEB-OPS-004, `ops`): never locked, and back to the project there.

const GeofenceMap = dynamic(() => import("@/common/map/geofence-map").then((m) => m.GeofenceMap), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

async function searchNominatim(q: string): Promise<LatLon | null> {
  const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ng&q=${encodeURIComponent(q)}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) return null;
  const hits = (await res.json()) as { lat: string; lon: string }[];
  const first = hits[0];
  return first ? { lat: Number(first.lat), lon: Number(first.lon) } : null;
}

/**
 * Finds the area of a site address with OpenStreetMap's Nominatim (same provider as the map tiles); null if not
 * found. Addresses are free text ("Shopping Mall, Old Abakaliki Rd, GRA, ..., Enugu State") and the whole string
 * rarely matches, so it tries the full text, then each part with the last part (usually the state) as context,
 * then the last part alone. One request a second, as Nominatim's policy asks.
 */
async function geocodeAddress(address: string): Promise<LatLon | null> {
  const parts = address
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const context = parts.length > 1 ? parts[parts.length - 1] : "";
  const tries = [
    address,
    ...parts.slice(0, -1).map((part) => `${part}, ${context}`),
    ...(context ? [context] : []),
  ];
  for (const [i, q] of tries.entries()) {
    if (i > 0) await new Promise((r) => setTimeout(r, 1100));
    const found = await searchNominatim(q).catch(() => null);
    if (found) return found;
  }
  return null;
}

/** About 90 m a side around the pin, like the seeded sites. */
function squareAround(p: LatLon, half = 0.0004): LatLon[] {
  return [
    { lat: p.lat - half, lon: p.lon - half },
    { lat: p.lat - half, lon: p.lon + half },
    { lat: p.lat + half, lon: p.lon + half },
    { lat: p.lat + half, lon: p.lon - half },
  ];
}

/** Further than this from the address area, the pin is probably in the wrong place. */
const FAR_FROM_ADDRESS_M = 50_000;

/** Puts the pin where the person is standing (browser GPS) and says how accurate the fix is (phones drift 5 to 20 m). */
function LocateButton({ onPin }: { onPin: (p: LatLon) => void }) {
  const [state, setState] = useState<{ busy: boolean; note: string | null }>({ busy: false, note: null });
  const locate = () => {
    if (!("geolocation" in navigator))
      return setState({ busy: false, note: "This browser can’t share a location." });
    setState({ busy: true, note: null });
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        onPin({ lat: coords.latitude, lon: coords.longitude });
        const m = Math.round(coords.accuracy);
        setState({
          busy: false,
          note:
            m > 25
              ? `Pin set, but the phone is only sure to about ${m} m. Move into the open and try again for a better fix.`
              : `Pin set to where you are (accurate to about ${m} m).`,
        });
      },
      () =>
        setState({
          busy: false,
          note: "We couldn’t get your location. Allow location access, or place the pin on the map.",
        }),
      { enableHighAccuracy: true, timeout: 20_000, maximumAge: 0 },
    );
  };
  return (
    <div className="flex flex-col gap-2">
      <Button type="button" variant="outline" loading={state.busy} onClick={locate}>
        <LocateFixed aria-hidden strokeWidth={1.75} className="size-4" />
        Use my current location
      </Button>
      {state.note ? (
        <p role="status" className="type-small text-slate">
          {state.note}
        </p>
      ) : null}
    </div>
  );
}

/**
 * The pin's coordinates, always on the page and open by default. While drawing they can be typed (and
 * give keyboard users a way to set the site); when the site is only being viewed they are read-only.
 */
function Coordinates({
  pin,
  readOnly,
  onPin,
  onSquare,
}: {
  pin: LatLon | null;
  readOnly: boolean;
  onPin: (p: LatLon) => void;
  onSquare: () => void;
}) {
  const ids = { lat: useId(), lon: useId() };
  const [lat, setLat] = useState(pin ? String(pin.lat) : "");
  const [lon, setLon] = useState(pin ? String(pin.lon) : "");
  // Follow the pin when it is moved on the map or by "Use my current location".
  const [shown, setShown] = useState(pin);
  if (pin !== shown) {
    setShown(pin);
    setLat(pin ? String(pin.lat) : "");
    setLon(pin ? String(pin.lon) : "");
  }
  const valid = Number.isFinite(Number(lat)) && Number.isFinite(Number(lon)) && lat !== "" && lon !== "";
  return (
    <details open className="rounded-card border border-line p-4">
      <summary className="cursor-pointer rounded-control font-semibold text-ink">Coordinates</summary>
      <div className="mt-3 flex flex-col gap-3">
        <p className="type-small text-slate">
          {readOnly
            ? "The pin's latitude and longitude."
            : "Type the plot's coordinates to place the pin, then use a square boundary around them if you can't draw one."}
        </p>
        <div className="grid grid-cols-2 gap-3">
          <label htmlFor={ids.lat} className="type-small flex flex-col gap-1 font-semibold text-ink">
            Latitude
            <input
              id={ids.lat}
              inputMode="decimal"
              value={lat}
              readOnly={readOnly}
              placeholder={readOnly ? "Not set" : undefined}
              onChange={(e) => setLat(e.target.value)}
              className="min-h-11 rounded-control border border-line-strong bg-white px-3 font-normal"
            />
          </label>
          <label htmlFor={ids.lon} className="type-small flex flex-col gap-1 font-semibold text-ink">
            Longitude
            <input
              id={ids.lon}
              inputMode="decimal"
              value={lon}
              readOnly={readOnly}
              placeholder={readOnly ? "Not set" : undefined}
              onChange={(e) => setLon(e.target.value)}
              className="min-h-11 rounded-control border border-line-strong bg-white px-3 font-normal"
            />
          </label>
        </div>
        {readOnly ? null : (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!valid}
              onClick={() => onPin({ lat: Number(lat), lon: Number(lon) })}
            >
              Set the pin here
            </Button>
            <Button type="button" variant="outline" disabled={!pin} onClick={onSquare}>
              Square boundary around the pin (about 90 m)
            </Button>
          </div>
        )}
      </div>
    </details>
  );
}

export function SiteEditor({ projectId, ops = false }: { projectId: string; ops?: boolean }) {
  const timeZone = useViewerTimeZone();
  const project = useProject(projectId);
  const save = useSaveSite(projectId);
  const siteSaved = Boolean(project.data?.site);
  const addressArea = useQuery({
    queryKey: ["geocode", project.data?.address],
    queryFn: () => geocodeAddress(project.data?.address ?? ""),
    enabled: Boolean(project.data?.address) && !siteSaved,
    staleTime: Infinity,
    retry: false,
  });
  const [draft, setDraft] = useState<{ pin: LatLon | null; corners: LatLon[] } | null>(null);
  const [mode, setMode] = useState<MapMode>("pin");
  const [editing, setEditing] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  if (project.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the site">
          <Skeleton className="h-96 w-full" />
        </Loading>
      </div>
    );
  if (!project.data) return <ServerErrorContent reference={null} onRetry={() => void project.refetch()} />;

  const p = project.data;
  const saved = p.site
    ? { pin: { lat: p.site.location.lat, lon: p.site.location.lon }, corners: fromGeoJson(p.site.geofence) }
    : null;
  const lockedByStatus = !ops && !(p.status === "draft" || p.status === "boq_review");
  const back = ops
    ? { href: `/ops/projects/${p.id}`, label: "Back to the project" }
    : { href: `/projects/${p.id}/setup`, label: "Back to set-up" };
  const lockedByServer = save.error instanceof ApiError && save.error.code === "site_locked";
  const locked = lockedByStatus || lockedByServer;
  const drawing = !locked && (editing || !saved);
  const shape = drawing
    ? (draft ?? saved ?? { pin: null, corners: [] })
    : (saved ?? { pin: null, corners: [] });
  const closed = shape.corners.length >= 3;
  const pinInside = shape.pin && closed ? insidePolygon(shape.pin, shape.corners) : null;
  const serverOutside = save.error instanceof ApiError && save.error.code === "pin_outside_geofence";

  const update = (next: { pin: LatLon | null; corners: LatLon[] }) => {
    setDraft(next);
    setProblem(null);
    save.reset();
  };

  const submit = () => {
    if (!shape.pin) return setProblem("Put the pin on your plot first.");
    if (!closed) return setProblem("Draw the boundary: at least three corners.");
    if (pinInside === false) return setProblem("outside");
    save.mutate(
      { location: { lat: shape.pin.lat, lon: shape.pin.lon }, geofence: toGeoJson(shape.corners) },
      {
        onSuccess: () => {
          setEditing(false);
          setDraft(null);
        },
      },
    );
  };

  const outside = problem === "outside" || serverOutside;
  const farFromAddress =
    drawing && shape.pin && addressArea.data
      ? metresBetween(shape.pin, addressArea.data) > FAR_FROM_ADDRESS_M
      : false;
  const status = locked
    ? { label: "Locked", tone: "neutral" as const }
    : outside
      ? { label: "Can’t save", tone: "bad" as const }
      : drawing
        ? { label: "Draft · editable", tone: "neutral" as const }
        : {
            label: ops ? "Saved · ops can change it" : "Saved · editable until approval",
            tone: "ok" as const,
          };

  const tools: { mode: MapMode | "undo" | "clear"; label: string; icon: typeof MapPin }[] = [
    { mode: "boundary", label: "Boundary", icon: Pentagon },
    { mode: "pin", label: "Pin", icon: MapPin },
    { mode: "undo", label: "Undo", icon: Undo2 },
    { mode: "clear", label: "Clear", icon: Trash2 },
  ];

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-6 sm:px-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Link href={back.href} className="type-small rounded-control font-semibold text-accent">
            ‹ {ops ? "Project" : "Set-up"}
          </Link>
          <h2 className="type-h1 text-ink">Site and boundary</h2>
        </div>
        <ToneChip label={status.label} tone={status.tone} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="relative h-96 lg:col-span-2 lg:h-150">
          <GeofenceMap
            label="Site map: the pin and the boundary"
            pin={shape.pin}
            corners={shape.corners}
            focus={addressArea.data ?? null}
            mode={drawing ? mode : "view"}
            locked={!drawing}
            onPin={(pin) => update({ pin, corners: shape.corners })}
            onAddCorner={(c) => update({ pin: shape.pin, corners: [...shape.corners, c] })}
            onMoveCorner={(i, c) =>
              update({ pin: shape.pin, corners: shape.corners.map((x, j) => (j === i ? c : x)) })
            }
            className="h-full w-full"
          />
          {drawing ? (
            <div
              role="toolbar"
              aria-label="Drawing tools"
              className="absolute top-3 left-3 z-10 flex gap-1 rounded-control bg-white p-1 shadow-raised"
            >
              {tools.map(({ mode: m, label, icon: Icon }) => (
                <button
                  key={m}
                  type="button"
                  aria-pressed={m === "boundary" || m === "pin" ? mode === m : undefined}
                  disabled={
                    (m === "undo" && !shape.corners.length) || (m === "clear" && !shape.corners.length)
                  }
                  onClick={() => {
                    if (m === "undo") update({ pin: shape.pin, corners: shape.corners.slice(0, -1) });
                    else if (m === "clear") update({ pin: shape.pin, corners: [] });
                    else setMode(m);
                  }}
                  className={cn(
                    "type-small flex min-h-9 items-center gap-1.5 rounded-control px-3 font-semibold text-ink disabled:text-muted",
                    (m === "boundary" || m === "pin") && mode === m ? "bg-accent-tint" : "hover:bg-mist",
                  )}
                >
                  <Icon aria-hidden strokeWidth={1.75} className="size-4" />
                  {label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <aside className="flex flex-col gap-4">
          {locked ? (
            <Alert tone="neutral" title="This site is locked">
              It was fixed when the BoQ was approved, so evidence rules can&apos;t change mid-build. Our team
              can update it if the plot really changed.
            </Alert>
          ) : outside ? (
            <Alert tone="bad" title="The pin is outside the boundary">
              Move the pin onto the plot, or redraw the boundary to include it.
            </Alert>
          ) : problem ? (
            <Alert tone="warn" title={problem} />
          ) : farFromAddress ? (
            <Alert tone="warn" title="The pin is far from the site address">
              It is more than 50 km from the address on this project. Check the pin is on the right plot.
            </Alert>
          ) : save.error ? (
            <Alert tone="bad" title="The site wasn’t saved">
              Nothing changed. Try again.
            </Alert>
          ) : null}
          <Card className="overflow-hidden">
            <ol>
              <li className="flex items-start gap-3 border-b border-line p-4">
                <StepMark done={Boolean(shape.pin) && pinInside !== false} bad={pinInside === false} n={1} />
                <div>
                  <p className="font-semibold text-ink">{ops ? "Pin on the plot" : "Pin on your plot"}</p>
                  <p className="type-small text-slate">
                    {!shape.pin
                      ? drawing
                        ? "Choose Pin, then click your plot on the map"
                        : "Not set"
                      : pinInside === false
                        ? "Currently outside the boundary"
                        : drawing
                          ? "Drag the pin to move it"
                          : "Inside the boundary"}
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3 p-4">
                <StepMark done={closed} n={2} />
                <div>
                  <p className="font-semibold text-ink">{drawing ? "Draw the boundary" : "Boundary saved"}</p>
                  <p className="type-small text-slate">
                    {drawing
                      ? `Choose Boundary, then click the map to add corners. ${shape.corners.length} ${shape.corners.length === 1 ? "corner" : "corners"} so far.`
                      : `${p.site ? formatDateTime(p.site.updated_at, timeZone) : ""}${locked ? " · locked" : ops ? " · every change is audited" : " · you can change it until the BoQ is approved"}`}
                  </p>
                </div>
              </li>
            </ol>
          </Card>
          <p className="type-small text-slate">
            Photos and videos are accepted only from inside this boundary. To allow for GPS drift, we accept
            captures up to 25 m outside the line.
          </p>
          {!drawing ? (
            <Coordinates pin={shape.pin} readOnly onPin={() => undefined} onSquare={() => undefined} />
          ) : null}
          {drawing ? (
            <>
              <LocateButton onPin={(pin) => update({ pin, corners: shape.corners })} />
              <Coordinates
                pin={shape.pin}
                readOnly={false}
                onPin={(pin) => update({ pin, corners: shape.corners })}
                onSquare={() => shape.pin && update({ pin: shape.pin, corners: squareAround(shape.pin) })}
              />
              <Button size="lg" block loading={save.isPending} onClick={submit}>
                Save site
              </Button>
            </>
          ) : locked ? null : (
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="outline" size="lg">
                <Link href={back.href}>{back.label}</Link>
              </Button>
              <Button size="lg" onClick={() => setEditing(true)}>
                Edit site
              </Button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function StepMark({ done, bad, n }: { done: boolean; bad?: boolean; n: number }) {
  return (
    <span
      className={cn(
        "type-small flex size-7 flex-none items-center justify-center rounded-pill font-semibold",
        bad
          ? "bg-bad-bg text-bad-fg"
          : done
            ? "bg-navy-900 text-white"
            : "border-2 border-accent text-accent",
      )}
    >
      {bad ? (
        <CircleAlert aria-hidden strokeWidth={2} className="size-4" />
      ) : done ? (
        <Check aria-hidden strokeWidth={2.5} className="size-4" />
      ) : (
        n
      )}
      <span className="sr-only">{bad ? " (problem)" : done ? " (done)" : ""}</span>
    </span>
  );
}
