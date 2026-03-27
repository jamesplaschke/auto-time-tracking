/**
 * Formats a prediction time into a human-readable countdown.
 * Returns { text, unit, cssClass } for rendering.
 */
export function formatCountdown(isoTime: string | null): {
  text: string;
  unit: string;
  cssClass: string;
} {
  if (!isoTime) {
    return { text: "--", unit: "", cssClass: "" };
  }

  const target = new Date(isoTime).getTime();
  const now = Date.now();
  const diffMs = target - now;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 0) {
    return { text: "BRD", unit: "", cssClass: "arriving" };
  }

  if (diffSec < 30) {
    return { text: "ARR", unit: "", cssClass: "arriving" };
  }

  if (diffSec < 60) {
    return { text: `${diffSec}`, unit: "sec", cssClass: "arriving" };
  }

  const minutes = Math.floor(diffSec / 60);

  if (minutes < 5) {
    return { text: `${minutes}`, unit: "min", cssClass: "soon" };
  }

  return { text: `${minutes}`, unit: "min", cssClass: "" };
}

let animFrameId: number | null = null;
let updateCallback: (() => void) | null = null;

export function startCountdownLoop(callback: () => void): void {
  updateCallback = callback;

  let lastUpdate = 0;
  function throttledTick() {
    const now = Date.now();
    if (now - lastUpdate >= 1000) {
      lastUpdate = now;
      updateCallback?.();
    }
    animFrameId = requestAnimationFrame(throttledTick);
  }

  throttledTick();
}

export function stopCountdownLoop(): void {
  if (animFrameId !== null) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
  updateCallback = null;
}
