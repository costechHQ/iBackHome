"use client";

import "leaflet/dist/leaflet.css";

import type { LayerGroup, Map as LeafletMap } from "leaflet";
import { useEffect, useRef, useState, type RefObject } from "react";

import { cn } from "../ui/cn";
import { toleranceRing, type LatLon } from "./geo";

// Geofence map (components.md): the site boundary (navy 2px, 8% fill), the dashed 25 m tolerance band, the
// site pin, and capture points. Leaflet, loaded in the browser only. Colours come from the design tokens at
// run time. Tiles are OpenStreetMap's for local and staging; production needs a tile provider with a key
// (PACKAGE-REPORT W-30). The map is never the only way to read or set anything: the screens around it say
// inside/outside in words and offer a keyboard way to set the site.

export type MapMode = "view" | "pin" | "boundary";

export type CapturePoint = LatLon & { label: string; inside: boolean };

type Handlers = {
  mode: MapMode;
  locked: boolean;
  onPin?: (p: LatLon) => void;
  onAddCorner?: (p: LatLon) => void;
  onMoveCorner?: (index: number, p: LatLon) => void;
};

type Shapes = {
  pin: LatLon | null;
  corners: readonly LatLon[];
  mode: MapMode;
  locked: boolean;
  captures: readonly CapturePoint[];
};

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
/** The middle of Nigeria, zoomed out to show the whole country, when there is no pin yet: sites can be anywhere. */
export const NIGERIA: LatLon = { lat: 9.082, lon: 8.6753 };

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(`--ibh-${name}`).trim();
}

const latLng = (c: LatLon) => [c.lat, c.lon] as [number, number];

/** Redraws every shape on the map's layer group from the current props. */
function drawLayers(
  L: typeof import("leaflet"),
  group: LayerGroup,
  s: Shapes,
  handlers: RefObject<Handlers>,
) {
  group.clearLayers();
  const navy = token("navy-900");
  const white = token("white");
  const editable = !s.locked && s.mode !== "view";

  if (s.corners.length >= 3) {
    L.polygon(toleranceRing(s.corners).map(latLng), {
      color: token("accent"),
      weight: 1.5,
      dashArray: "6 6",
      fill: false,
      interactive: false,
    }).addTo(group);
    L.polygon(s.corners.map(latLng), {
      color: navy,
      weight: 2,
      fillColor: navy,
      fillOpacity: 0.08,
      interactive: false,
    }).addTo(group);
  } else if (s.corners.length === 2) {
    L.polyline(s.corners.map(latLng), { color: navy, weight: 2 }).addTo(group);
  }

  if (s.mode === "boundary" && editable) {
    s.corners.forEach((c, i) => {
      const handle = L.marker(latLng(c), {
        draggable: true,
        keyboard: false,
        icon: L.divIcon({ className: "ibh-map-corner", iconSize: [14, 14] }),
        title: `Corner ${i + 1}`,
      }).addTo(group);
      handle.on("dragend", () => {
        const at = handle.getLatLng();
        handlers.current?.onMoveCorner?.(i, { lat: at.lat, lon: at.lng });
      });
    });
  }

  for (const c of s.captures) {
    L.circleMarker(latLng(c), {
      radius: 6,
      color: c.inside ? navy : token("bad-fg"),
      weight: 2,
      fillColor: white,
      fillOpacity: 1,
    })
      .bindTooltip(c.label)
      .addTo(group);
  }

  if (s.pin) {
    const marker = L.marker(latLng(s.pin), {
      draggable: editable,
      keyboard: false,
      icon: L.divIcon({
        className: "ibh-map-pin",
        html: `<svg viewBox="0 0 24 32" width="30" height="40" aria-hidden="true"><path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20s12-11 12-20C24 5.4 18.6 0 12 0z" fill="${navy}" stroke="${white}" stroke-width="1.5"/><circle cx="12" cy="12" r="4" fill="${white}"/></svg>`,
        iconSize: [30, 40],
        iconAnchor: [15, 40],
      }),
      title: "Site pin",
    }).addTo(group);
    marker.on("dragend", () => {
      const at = marker.getLatLng();
      handlers.current?.onPin?.({ lat: at.lat, lon: at.lng });
    });
  }
}

export function GeofenceMap({
  pin,
  corners,
  mode = "view",
  locked = false,
  captures = [],
  onPin,
  onAddCorner,
  onMoveCorner,
  label,
  className,
}: {
  pin: LatLon | null;
  corners: readonly LatLon[];
  mode?: MapMode;
  locked?: boolean;
  captures?: readonly CapturePoint[];
  onPin?: (p: LatLon) => void;
  onAddCorner?: (p: LatLon) => void;
  onMoveCorner?: (index: number, p: LatLon) => void;
  label: string;
  className?: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const layers = useRef<LayerGroup | null>(null);
  const leaflet = useRef<typeof import("leaflet") | null>(null);
  const handlers = useRef<Handlers>({ mode, locked, onPin, onAddCorner, onMoveCorner });
  const [ready, setReady] = useState(false);
  const start = useRef(pin ?? corners[0] ?? null);

  // The latest props for the map's own event handlers.
  useEffect(() => {
    handlers.current = { mode, locked, onPin, onAddCorner, onMoveCorner };
  });

  // Create the map once.
  useEffect(() => {
    let cancelled = false;
    void import("leaflet").then((L) => {
      if (cancelled || !box.current || map.current) return;
      leaflet.current = L;
      const at = start.current ?? NIGERIA;
      const m = L.map(box.current, { zoomControl: true, attributionControl: true }).setView(
        [at.lat, at.lon],
        start.current ? 18 : 6,
      );
      L.tileLayer(TILES, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(m);
      m.on("click", (e) => {
        const { mode: now, locked: frozen, onPin: setPin, onAddCorner: add } = handlers.current;
        if (frozen) return;
        const p = { lat: e.latlng.lat, lon: e.latlng.lng };
        if (now === "boundary") add?.(p);
        else if (now === "pin") setPin?.(p);
      });
      map.current = m;
      layers.current = L.layerGroup().addTo(m);
      setReady(true);
    });
    return () => {
      cancelled = true;
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // Redraw the shapes whenever they change.
  useEffect(() => {
    if (!ready || !leaflet.current || !layers.current) return;
    drawLayers(leaflet.current, layers.current, { pin, corners, mode, locked, captures }, handlers);
  }, [ready, pin, corners, mode, locked, captures]);

  // Showing (not drawing) a boundary: fit the map to it, e.g. right after it is saved.
  const shapeKey = mode === "view" && corners.length >= 3 ? JSON.stringify(corners) : "";
  useEffect(() => {
    if (!ready || !shapeKey || !map.current || !leaflet.current) return;
    const bounds = leaflet.current.latLngBounds((JSON.parse(shapeKey) as LatLon[]).map(latLng));
    map.current.fitBounds(bounds, { padding: [48, 48], maxZoom: 19 });
  }, [ready, shapeKey]);

  // Bring a pin set from outside the map (typed coordinates) into view.
  useEffect(() => {
    if (ready && pin && map.current && !map.current.getBounds().contains([pin.lat, pin.lon])) {
      map.current.setView([pin.lat, pin.lon], Math.max(map.current.getZoom(), 17));
    }
  }, [ready, pin]);

  return (
    <div
      ref={box}
      role="region"
      aria-label={label}
      className={cn("ibh-map z-0 overflow-hidden rounded-card border border-line bg-mist", className)}
    />
  );
}
