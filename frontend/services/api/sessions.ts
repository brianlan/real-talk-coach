const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const wsBase = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000/ws";

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

export function connectSessionSocket(sessionId: string): WebSocket {
  return new WebSocket(`${wsBase}/sessions/${sessionId}`);
}
