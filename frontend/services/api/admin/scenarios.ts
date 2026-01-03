const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const adminToken = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

export type ScenarioInput = {
  category: string;
  title: string;
  description: string;
  objective: string;
  aiPersona: { name: string; role: string; background: string };
  traineePersona: { name: string; role: string; background: string };
  endCriteria: string[];
  skills: string[];
  prompt: string;
  idleLimitSeconds?: number;
  durationLimitSeconds?: number;
  status?: string;
};

export type Scenario = ScenarioInput & {
  id: string;
  recordStatus?: string;
  version?: string | null;
};

function authHeaders(extra?: Record<string, string>) {
  return {
    "Content-Type": "application/json",
    ...(adminToken ? { "X-Admin-Token": adminToken } : {}),
    ...(extra ?? {}),
  } as Record<string, string>;
}

export async function listScenarios(includeDeleted = false): Promise<Scenario[]> {
  const res = await fetch(
    `${apiBase}/api/admin/scenarios?include_deleted=${includeDeleted ? "true" : "false"}`,
    { headers: authHeaders() }
  );
  if (!res.ok) throw new Error("Failed to load scenarios");
  const body = await res.json();
  return body.scenarios ?? [];
}

export async function getScenario(id: string): Promise<Scenario> {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) throw new Error("Not found");
  if (!res.ok) throw new Error("Failed to load scenario");
  return res.json();
}

export async function createScenario(input: ScenarioInput) {
  const res = await fetch(`${apiBase}/api/admin/scenarios`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to create scenario");
  }
  return res.json();
}

export async function updateScenario(id: string, input: Partial<ScenarioInput>, version: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    method: "PUT",
    headers: authHeaders({ "If-Match": version }),
    body: JSON.stringify(input),
  });
  if (res.status === 409) throw new Error("stale");
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to update scenario");
  }
  return res.json();
}

export async function publishScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/publish`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to publish scenario");
  return res.json();
}

export async function unpublishScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/unpublish`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to unpublish scenario");
  return res.json();
}

export async function deleteScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status === 409) throw new Error("in-use");
  if (res.status !== 204 and res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete scenario");
  }
}

export async function restoreScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/restore`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to restore scenario");
  return res.json();
}
