import { renderAlerts } from "./components/alert-banner.ts";
import { renderLeaveNowAlerts } from "./components/leave-now-banner.ts";
import {
  renderSettings,
  setupSettingsToggle,
} from "./components/settings-panel.ts";
import {
  groupPredictions,
  renderStopCard,
  updateCountdowns,
} from "./components/stop-card.ts";
import { startCountdownLoop } from "./countdown.ts";
import {
  getAllRouteIds,
  getUniqueStopIds,
  getWalkTimesJson,
  loadPreferences,
  savePreferences,
} from "./preferences.ts";
import { connectSSE } from "./sse.ts";
import type { LeaveNowAlert, Prediction, ServiceAlert } from "./types.ts";

// ---- State ----
let currentPredictions: Prediction[] = [];
let currentAlerts: ServiceAlert[] = [];
let currentLeaveNow: LeaveNowAlert[] = [];
let notifiedPredictions = new Set<string>();

// ---- DOM refs ----
const stopsGrid = document.getElementById("stops-grid")!;
const alertsContainer = document.getElementById("alerts-container")!;
const leaveNowContainer = document.getElementById("leave-now-container")!;
const clockEl = document.getElementById("clock")!;

// ---- Clock ----
function updateClock(): void {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

// ---- Rendering ----
function renderStops(): void {
  const prefs = loadPreferences();
  const groups = groupPredictions(currentPredictions, prefs.stops);

  stopsGrid.innerHTML = groups.map(renderStopCard).join("");
}

function renderAlertBanners(): void {
  alertsContainer.innerHTML = renderAlerts(currentAlerts);
}

function renderLeaveNow(): void {
  leaveNowContainer.innerHTML = renderLeaveNowAlerts(currentLeaveNow);
  triggerNotifications();
}

// ---- Browser Notifications ----
function triggerNotifications(): void {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;

  for (const alert of currentLeaveNow) {
    if (alert.urgency !== "now") continue;
    const key = `${alert.stop_id}-${alert.route_id}-${alert.prediction_time}`;
    if (notifiedPredictions.has(key)) continue;

    notifiedPredictions.add(key);
    new Notification(`Leave NOW for ${alert.stop_name}!`, {
      body: `${alert.route_id} line train in ${alert.walk_minutes} min`,
      icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚇</text></svg>",
      tag: key,
    });
  }
}

// ---- SSE Connection ----
function startStream(): void {
  const prefs = loadPreferences();
  const stopIds = getUniqueStopIds(prefs.stops);
  const routeIds = getAllRouteIds(prefs.stops);
  const walkTimes = getWalkTimesJson(prefs.stops);

  if (stopIds.length === 0) {
    stopsGrid.innerHTML = '<div class="loading">No stops configured. Open settings to add stops.</div>';
    return;
  }

  stopsGrid.innerHTML = '<div class="loading">Connecting to MBTA...</div>';

  connectSSE(stopIds, routeIds, walkTimes, {
    onPredictions: (preds) => {
      currentPredictions = preds;
      renderStops();
    },
    onAlerts: (alerts) => {
      currentAlerts = alerts;
      renderAlertBanners();
    },
    onLeaveNow: (alerts) => {
      currentLeaveNow = alerts;
      renderLeaveNow();
    },
    onError: () => {
      // EventSource reconnects automatically; no action needed
    },
  });
}

// ---- Mirror Mode ----
function initMirrorMode(): void {
  const prefs = loadPreferences();
  const params = new URLSearchParams(window.location.search);
  const mirrorParam = params.get("mode") === "mirror";

  if (mirrorParam || prefs.mirrorMode) {
    document.body.classList.add("mirror-mode");
    prefs.mirrorMode = true;
    savePreferences(prefs);

    // Try to request wake lock
    requestWakeLock();

    // Auto-hide cursor
    let cursorTimeout: ReturnType<typeof setTimeout>;
    document.addEventListener("mousemove", () => {
      document.body.classList.add("cursor-visible");
      clearTimeout(cursorTimeout);
      cursorTimeout = setTimeout(() => {
        document.body.classList.remove("cursor-visible");
      }, 3000);
    });

    // Fullscreen on click
    document.body.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {
          // Ignore if not supported
        });
      }
    }, { once: true });
  }

  const mirrorBtn = document.getElementById("mirror-toggle");
  mirrorBtn?.addEventListener("click", () => {
    const p = loadPreferences();
    p.mirrorMode = !p.mirrorMode;
    savePreferences(p);
    document.body.classList.toggle("mirror-mode", p.mirrorMode);
    if (p.mirrorMode) requestWakeLock();
  });
}

async function requestWakeLock(): Promise<void> {
  try {
    if ("wakeLock" in navigator) {
      await (navigator as Navigator & { wakeLock: { request: (type: string) => Promise<unknown> } }).wakeLock.request("screen");
    }
  } catch {
    // Wake Lock not available or denied
  }
}

// ---- Notification Permission ----
function requestNotificationPermission(): void {
  if ("Notification" in window && Notification.permission === "default") {
    // Request after first user interaction
    document.body.addEventListener(
      "click",
      () => {
        Notification.requestPermission();
      },
      { once: true },
    );
  }
}

// ---- Init ----
function init(): void {
  updateClock();
  initMirrorMode();
  setupSettingsToggle();

  renderSettings(() => {
    // Re-connect SSE with updated preferences
    startStream();
  });

  startStream();

  // Update countdowns every second
  startCountdownLoop(() => {
    updateClock();
    updateCountdowns();
  });

  requestNotificationPermission();
}

init();
