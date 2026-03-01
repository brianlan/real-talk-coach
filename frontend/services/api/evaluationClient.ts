import { getApiBase } from "./base";

const apiBase = getApiBase();

export type EvaluationScore = {
  skillId: string;
  rating: number;
  note: string;
};

export type Evaluation = {
  sessionId: string;
  status: "pending" | "running" | "failed" | "completed";
  scores: EvaluationScore[];
  summary?: string | null;
  evaluatorModel?: string | null;
  attempts?: number | null;
  lastError?: string | null;
  queuedAt?: string | null;
  completedAt?: string | null;
};

export async function fetchEvaluation(sessionId: string): Promise<Evaluation | null> {
  const response = await fetch(`${apiBase}/api/sessions/${sessionId}/evaluation`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Evaluation fetch failed (${response.status})`);
  }
  return response.json();
}

export async function requeueEvaluation(sessionId: string): Promise<Evaluation> {
  const response = await fetch(`${apiBase}/api/sessions/${sessionId}/evaluation`, {
    method: "POST",
  });
  if (!response.ok && response.status !== 409) {
    throw new Error(`Evaluation requeue failed (${response.status})`);
  }
  return response.json();
}
