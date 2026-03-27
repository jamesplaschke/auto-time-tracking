import { getRouteColor } from "../preferences.ts";
import type { ServiceAlert } from "../types.ts";

export function renderAlerts(alerts: ServiceAlert[]): string {
  if (alerts.length === 0) return "";

  return alerts
    .map((alert) => {
      const severe = alert.severity >= 7;
      const routeBadges = alert.affected_routes
        .map((r) => {
          const color = getRouteColor(r);
          return `<span class="route-badge" style="background:${color}">${r}</span>`;
        })
        .join("");

      return `
        <div class="alert-banner${severe ? " severe" : ""}">
          <div class="alert-routes">${routeBadges}</div>
          <div class="alert-header">${escapeHtml(alert.header)}</div>
        </div>
      `;
    })
    .join("");
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
