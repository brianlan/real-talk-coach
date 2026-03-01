import { getApiBase } from "./base";

const apiBase = getApiBase();

export type HistoryListFilters = {
  page?: number;
  pageSize?: number;
  scenarioId?: string;
  category?: string;
  search?: string;
  sort?: "startedAtDesc" | "startedAtAsc";
  historyStepCount: number;
  userId?: string;
};

export type SessionSummary = {
  id: string;
  scenarioId: string;
  status: string;
  startedAt?: string | null;
  endedAt?: string | null;
  terminationReason?: string | null;
};

export type SessionPage = {
  items: SessionSummary[];
  page: number;
  pageSize: number;
  total: number;
};

export async function fetchHistoryList(filters: HistoryListFilters): Promise<SessionPage> {
  const query = new URLSearchParams({
    historyStepCount: String(filters.historyStepCount),
    page: String(filters.page ?? 1),
    pageSize: String(filters.pageSize ?? 20),
  });
  if (filters.scenarioId) {
    query.set("scenarioId", filters.scenarioId);
  }
  if (filters.category) {
    query.set("category", filters.category);
  }
  if (filters.search) {
    query.set("search", filters.search);
  }
  if (filters.sort) {
    query.set("sort", filters.sort);
  }
  const response = await fetch(`${apiBase}/api/sessions?${query}`, {
    cache: "no-store",
    headers: filters.userId ? { "X-User-Id": filters.userId } : undefined,
  });
  if (!response.ok) {
    throw new Error(`History fetch failed (${response.status})`);
  }
  return response.json();
}

export async function fetchHistoryDetail(
  sessionId: string,
  historyStepCount: number,
  userId?: string
) {
  const response = await fetch(
    `${apiBase}/api/sessions/${sessionId}?historyStepCount=${historyStepCount}`,
    {
      cache: "no-store",
      headers: userId ? { "X-User-Id": userId } : undefined,
    }
  );
  if (!response.ok) {
    throw new Error(`History detail fetch failed (${response.status})`);
  }
  return response.json();
}

export async function practiceAgain(sessionId: string) {
  const response = await fetch(`${apiBase}/api/sessions/${sessionId}/practice-again`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clientSessionStartedAt: new Date().toISOString() }),
  });
  if (!response.ok) {
    throw new Error(`Practice again failed (${response.status})`);
  }
  return response.json();
}
