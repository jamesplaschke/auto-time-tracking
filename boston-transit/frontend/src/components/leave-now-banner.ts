import type { LeaveNowAlert } from "../types.ts";

export function renderLeaveNowAlerts(alerts: LeaveNowAlert[]): string {
  // Only show non-missed alerts
  const active = alerts.filter((a) => a.urgency !== "missed");
  if (active.length === 0) return "";

  return active
    .slice(0, 3)
    .map((alert) => {
      const label = formatLeaveLabel(alert);
      const timeStr = formatLeaveTime(alert);

      return `
        <div class="leave-now-alert urgency-${alert.urgency}">
          <span class="leave-now-label">${label}</span>
          <span class="leave-now-time">${timeStr}</span>
        </div>
      `;
    })
    .join("");
}

function formatLeaveLabel(alert: LeaveNowAlert): string {
  const verb =
    alert.urgency === "now"
      ? "LEAVE NOW for"
      : alert.urgency === "soon"
        ? "Leave soon for"
        : "Upcoming";
  return `${verb} ${alert.stop_name} (${alert.route_id})`;
}

function formatLeaveTime(alert: LeaveNowAlert): string {
  if (alert.urgency === "now") return "GO!";
  const mins = Math.ceil(alert.minutes_until_leave);
  return `${mins} min`;
}
