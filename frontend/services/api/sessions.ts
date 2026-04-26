import { getApiBase, getWsBase } from "./base";

const apiBase = getApiBase();
const wsBase = getWsBase();

export async function manualStopSession(sessionId: string, reason = "manual") {
  await fetch(`${apiBase}/api/sessions/${sessionId}/manual-stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
}

export function manualStopSessionBestEffort(sessionId: string, reason = "manual"): boolean {
  if (typeof window === "undefined" || typeof navigator === "undefined" || typeof navigator.sendBeacon !== "function") {
    return false;
  }

  const payload = JSON.stringify({ reason });
  const blob = new Blob([payload], { type: "application/json" });
  return navigator.sendBeacon(`${apiBase}/api/sessions/${sessionId}/manual-stop`, blob);
}

export function connectSessionSocket(sessionId: string): WebSocket {
  return new WebSocket(`${wsBase}/sessions/${sessionId}`);
}

export type PracticeSessionCreate = {
  scenarioId: string;
  clientSessionStartedAt: string;
  userId?: string;
  language?: "en" | "zh";
};

export async function createSession(input: PracticeSessionCreate) {
  const res = await fetch(`${apiBase}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    let detail = "Failed to create session";
    try {
      const payload = await res.json();
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = `Failed to create session (${res.status})`;
    }
    throw new Error(detail);
  }
  return res.json();
}
