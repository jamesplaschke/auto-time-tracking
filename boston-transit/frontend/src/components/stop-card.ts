import { formatCountdown } from "../countdown.ts";
import { getRouteColor, getLineDisplayName } from "../preferences.ts";
import type { Prediction, StopPreference } from "../types.ts";

interface StopGroup {
  stopId: string;
  routeId: string;
  label: string;
  predictions: Prediction[];
}

/**
 * Group predictions by stop+route, matching the user's configured stops.
 */
export function groupPredictions(
  predictions: Prediction[],
  stops: StopPreference[],
): StopGroup[] {
  const groups: StopGroup[] = [];

  for (const pref of stops) {
    if (!pref.enabled) continue;

    const routeIds = pref.route_id.split(",").map((r) => r.trim());
    const matching = predictions.filter(
      (p) =>
        p.stop_id === pref.stop_id && routeIds.some((r) => p.route_id === r),
    );

    // Group further by route for multi-route stops
    const byRoute = new Map<string, Prediction[]>();
    for (const p of matching) {
      const existing = byRoute.get(p.route_id) || [];
      existing.push(p);
      byRoute.set(p.route_id, existing);
    }

    if (byRoute.size === 0) {
      // Still show the card even with no predictions
      groups.push({
        stopId: pref.stop_id,
        routeId: routeIds[0],
        label: pref.label || pref.stop_id,
        predictions: [],
      });
    } else {
      for (const [routeId, preds] of byRoute) {
        groups.push({
          stopId: pref.stop_id,
          routeId,
          label: pref.label || preds[0]?.stop_name || pref.stop_id,
          predictions: preds,
        });
      }
    }
  }

  return groups;
}

/**
 * Render a single stop card to HTML string.
 */
export function renderStopCard(group: StopGroup): string {
  const color = getRouteColor(group.routeId);
  const lineName = getLineDisplayName(group.routeId);

  if (group.predictions.length === 0) {
    return `
      <div class="stop-card" data-stop="${group.stopId}" data-route="${group.routeId}">
        <div class="stop-card-header">
          <div class="line-indicator" style="background:${color}"></div>
          <div>
            <div class="stop-name">${group.label}</div>
            <div class="route-name">${lineName} Line</div>
          </div>
        </div>
        <div class="no-predictions">No upcoming trains</div>
      </div>
    `;
  }

  // Split by direction
  const byDirection = new Map<number, Prediction[]>();
  for (const p of group.predictions) {
    const existing = byDirection.get(p.direction_id) || [];
    existing.push(p);
    byDirection.set(p.direction_id, existing);
  }

  let directionsHtml = "";
  for (const [dirId, preds] of byDirection) {
    const dirName =
      preds[0]?.direction_name || (dirId === 0 ? "Southbound" : "Northbound");
    const top3 = preds.slice(0, 3);

    let rowsHtml = "";
    for (const pred of top3) {
      const time = pred.departure_time || pred.arrival_time;
      const cd = formatCountdown(time);
      const statusText = pred.status || "";

      rowsHtml += `
        <div class="prediction-row">
          <span class="prediction-status">${statusText}</span>
          <span class="prediction-countdown ${cd.cssClass}" data-time="${time || ""}">
            ${cd.text}<span class="prediction-unit">${cd.unit}</span>
          </span>
        </div>
      `;
    }

    directionsHtml += `
      <div class="direction-group">
        <div class="direction-label">${dirName}</div>
        ${rowsHtml}
      </div>
    `;
  }

  return `
    <div class="stop-card" data-stop="${group.stopId}" data-route="${group.routeId}">
      <div class="stop-card-header">
        <div class="line-indicator" style="background:${color}"></div>
        <div>
          <div class="stop-name">${group.label}</div>
          <div class="route-name">${lineName} Line</div>
        </div>
      </div>
      ${directionsHtml}
    </div>
  `;
}

/**
 * Update all countdown displays in-place without full re-render.
 */
export function updateCountdowns(): void {
  const elements = document.querySelectorAll<HTMLElement>(
    ".prediction-countdown[data-time]",
  );
  for (const el of elements) {
    const time = el.getAttribute("data-time");
    if (!time) continue;
    const cd = formatCountdown(time);
    el.innerHTML = `${cd.text}<span class="prediction-unit">${cd.unit}</span>`;
    el.className = `prediction-countdown ${cd.cssClass}`;
  }
}
