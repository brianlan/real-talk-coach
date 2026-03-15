import { getApiBase, getWsBase } from "./base";

const apiBase = getApiBase();
const wsBase = getWsBase();

type TurnSubmitInput = {
  sessionId: string;
  sequence: number;
  audioBase64?: string;
  audioBlob?: Blob;
  startedAt: string;
  endedAt: string;
  context?: string | null;
};

type TurnSubmitResult = {
  status: number;
  data?: any;
  shouldResend: boolean;
  message?: string;
  audioBase64?: string;
};

async function blobToBase64(blob: Blob): Promise<string> {
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary);
}

export async function submitTurn(
  input: TurnSubmitInput
): Promise<TurnSubmitResult> {
  const audioBase64 =
    input.audioBase64 ?? (input.audioBlob ? await blobToBase64(input.audioBlob) : "");

  const response = await fetch(
    `${apiBase}/api/sessions/${input.sessionId}/turns`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sequence: input.sequence,
        audioBase64,
        context: input.context ?? null,
        startedAt: input.startedAt,
        endedAt: input.endedAt,
      }),
    }
  );

  const message = await response.text();
  const shouldResend =
    response.status === 422 && message.toLowerCase().includes("resend");

  let data: any;
  try {
    data = JSON.parse(message);
  } catch {
    data = undefined;
  }

  return {
    status: response.status,
    data,
    shouldResend,
    message,
    audioBase64,
  };
}

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
