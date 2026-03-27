import type { StopPreference } from "./types.ts";

const STORAGE_KEY = "boston-transit-prefs";

export interface Preferences {
  stops: StopPreference[];
  mirrorMode: boolean;
}

const DEFAULT_STOPS: StopPreference[] = [
  // Red Line
  { stop_id: "place-mghmn", route_id: "Red", walk_minutes: 2, enabled: true, label: "MGH" },
  { stop_id: "place-knncl", route_id: "Red", walk_minutes: 3, enabled: true, label: "Kendall/MIT" },
  { stop_id: "place-cntsq", route_id: "Red", walk_minutes: 0, enabled: true, label: "Central" },
  { stop_id: "place-dwnxg", route_id: "Red", walk_minutes: 0, enabled: true, label: "Downtown Crossing" },
  { stop_id: "place-pktrm", route_id: "Red", walk_minutes: 0, enabled: true, label: "Park Street" },
  // Orange Line
  { stop_id: "place-dwnxg", route_id: "Orange", walk_minutes: 0, enabled: true, label: "Downtown Crossing" },
  { stop_id: "place-ruggb", route_id: "Orange", walk_minutes: 0, enabled: true, label: "Ruggles" },
  // Green Line
  { stop_id: "place-pktrm", route_id: "Green-B,Green-C,Green-D,Green-E", walk_minutes: 0, enabled: true, label: "Park Street" },
  { stop_id: "place-kencl", route_id: "Green-B,Green-C,Green-D", walk_minutes: 0, enabled: true, label: "Kenmore" },
  { stop_id: "place-symcl", route_id: "Green-E", walk_minutes: 0, enabled: true, label: "Symphony" },
];

export function loadPreferences(): Preferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.stops && parsed.stops.length > 0) {
        return parsed;
      }
    }
  } catch {
    // Ignore parse errors
  }
  return { stops: DEFAULT_STOPS, mirrorMode: false };
}

export function savePreferences(prefs: Preferences): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function getWalkTimesJson(stops: StopPreference[]): string {
  const wt: Record<string, number> = {};
  for (const s of stops) {
    if (s.walk_minutes > 0 && s.enabled) {
      wt[s.stop_id] = s.walk_minutes;
    }
  }
  return JSON.stringify(wt);
}

export function getUniqueStopIds(stops: StopPreference[]): string[] {
  return [...new Set(stops.filter((s) => s.enabled).map((s) => s.stop_id))];
}

export function getAllRouteIds(stops: StopPreference[]): string[] {
  const routes = new Set<string>();
  for (const s of stops) {
    if (!s.enabled) continue;
    for (const r of s.route_id.split(",")) {
      routes.add(r.trim());
    }
  }
  return [...routes];
}

export const ROUTE_COLORS: Record<string, string> = {
  Red: "#DA291C",
  Orange: "#ED8B00",
  Blue: "#003DA5",
  "Green-B": "#00843D",
  "Green-C": "#00843D",
  "Green-D": "#00843D",
  "Green-E": "#00843D",
};

export function getRouteColor(routeId: string): string {
  return ROUTE_COLORS[routeId] || "#888";
}

export function getLineDisplayName(routeId: string): string {
  if (routeId.startsWith("Green-")) return "Green";
  return routeId;
}
