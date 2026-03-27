import type { LeaveNowAlert, Prediction, ServiceAlert } from "./types.ts";

export interface SSECallbacks {
  onPredictions: (preds: Prediction[]) => void;
  onAlerts: (alerts: ServiceAlert[]) => void;
  onLeaveNow: (alerts: LeaveNowAlert[]) => void;
  onError?: (error: Event) => void;
}

let currentSource: EventSource | null = null;

export function connectSSE(
  stopIds: string[],
  routeIds: string[],
  walkTimesJson: string,
  callbacks: SSECallbacks,
): EventSource {
  // Close existing connection
  if (currentSource) {
    currentSource.close();
  }

  const params = new URLSearchParams({
    stops: stopIds.join(","),
    routes: routeIds.join(","),
    walk_times: walkTimesJson,
  });

  const source = new EventSource(`/api/stream?${params}`);
  currentSource = source;

  source.addEventListener("predictions", (e) => {
    try {
      const data = JSON.parse(e.data) as Prediction[];
      callbacks.onPredictions(data);
    } catch {
      // Ignore parse errors
    }
  });

  source.addEventListener("alerts", (e) => {
    try {
      const data = JSON.parse(e.data) as ServiceAlert[];
      callbacks.onAlerts(data);
    } catch {
      // Ignore
    }
  });

  source.addEventListener("leave_now", (e) => {
    try {
      const data = JSON.parse(e.data) as LeaveNowAlert[];
      callbacks.onLeaveNow(data);
    } catch {
      // Ignore
    }
  });

  source.onerror = (e) => {
    callbacks.onError?.(e);
  };

  return source;
}

export function disconnectSSE(): void {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
}
