import {
  getRouteColor,
  loadPreferences,
  savePreferences,
} from "../preferences.ts";
import type { StopPreference } from "../types.ts";

type OnChangeCallback = () => void;

export function renderSettings(onChange: OnChangeCallback): void {
  const body = document.getElementById("settings-body");
  if (!body) return;

  const prefs = loadPreferences();
  const stops = prefs.stops;

  // Group by route
  const groups = new Map<string, StopPreference[]>();
  for (const s of stops) {
    const line = s.route_id.startsWith("Green") ? "Green" : s.route_id;
    const existing = groups.get(line) || [];
    existing.push(s);
    groups.set(line, existing);
  }

  let html = "";
  for (const [line, lineStops] of groups) {
    const color = getRouteColor(
      line === "Green" ? "Green-B" : line,
    );

    html += `<div class="setting-group">
      <h3 style="color:${color}">${line} Line</h3>`;

    for (let i = 0; i < lineStops.length; i++) {
      const s = lineStops[i];
      const globalIdx = stops.indexOf(s);
      html += `
        <div class="stop-setting">
          <span class="stop-setting-name">
            <span class="line-dot" style="background:${color}"></span>
            ${s.label || s.stop_id}
          </span>
          <div class="walk-time-input">
            <input type="number" min="0" max="60" value="${s.walk_minutes}"
                   data-idx="${globalIdx}" aria-label="Walk time in minutes" />
            <label>min walk</label>
          </div>
        </div>`;
    }

    html += `</div>`;
  }

  body.innerHTML = html;

  // Bind change handlers
  body.querySelectorAll<HTMLInputElement>("input[type=number]").forEach(
    (input) => {
      input.addEventListener("change", () => {
        const idx = parseInt(input.dataset.idx || "0");
        const val = parseInt(input.value) || 0;
        const p = loadPreferences();
        if (p.stops[idx]) {
          p.stops[idx].walk_minutes = Math.max(0, Math.min(60, val));
          savePreferences(p);
          onChange();
        }
      });
    },
  );
}

export function setupSettingsToggle(): void {
  const panel = document.getElementById("settings-panel");
  const toggleBtn = document.getElementById("settings-toggle");
  const closeBtn = document.getElementById("settings-close");
  const overlay = panel?.querySelector(".settings-overlay");

  const close = () => panel?.classList.add("hidden");
  const open = () => panel?.classList.remove("hidden");

  toggleBtn?.addEventListener("click", open);
  closeBtn?.addEventListener("click", close);
  overlay?.addEventListener("click", close);
}
