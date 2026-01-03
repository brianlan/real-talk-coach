const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const adminToken = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

export type Skill = {
  id: string;
  name: string;
  category: string;
  rubric: string;
  description?: string | null;
  status?: string;
  version?: string | null;
};

function authHeaders(extra?: Record<string, string>) {
  return {
    "Content-Type": "application/json",
    ...(adminToken ? { "X-Admin-Token": adminToken } : {}),
    ...(extra ?? {}),
  } as Record<string, string>;
}

export async function listSkills(includeDeleted = false): Promise<Skill[]> {
  const res = await fetch(
    `${apiBase}/api/admin/skills?include_deleted=${includeDeleted ? "true" : "false"}`,
    { headers: authHeaders() }
  );
  if (!res.ok) {
    throw new Error("Failed to load skills");
  }
  const body = await res.json();
  return body.skills ?? [];
}

export async function getSkill(id: string): Promise<Skill> {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) {
    throw new Error("Not found");
  }
  if (!res.ok) {
    throw new Error("Failed to load skill");
  }
  return res.json();
}

export async function createSkill(input: Omit<Skill, "id" | "version">) {
  const res = await fetch(`${apiBase}/api/admin/skills`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to create skill");
  }
  return res.json();
}

export async function updateSkill(
  id: string,
  input: Partial<Omit<Skill, "id">>,
  version: string
) {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}`, {
    method: "PUT",
    headers: authHeaders({ "If-Match": version }),
    body: JSON.stringify(input),
  });
  if (res.status === 409) {
    throw new Error("stale");
  }
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to update skill");
  }
  return res.json();
}

export async function deleteSkill(id: string) {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status !== 204 && res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete skill");
  }
}

export async function restoreSkill(id: string) {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}/restore`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to restore skill");
  }
  return res.json();
}
