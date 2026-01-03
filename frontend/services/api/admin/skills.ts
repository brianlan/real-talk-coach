import { adminApiBase, adminHeaders } from "./client";

const apiBase = adminApiBase();

export type Skill = {
  id: string;
  name: string;
  category: string;
  rubric: string;
  description?: string | null;
  status?: string;
  version?: string | null;
};

export async function listSkills(includeDeleted = false): Promise<Skill[]> {
  const res = await fetch(
    `${apiBase}/api/admin/skills?include_deleted=${includeDeleted ? "true" : "false"}`,
    { headers: adminHeaders() }
  );
  if (!res.ok) {
    throw new Error("Failed to load skills");
  }
  const body = await res.json();
  return body.skills ?? [];
}

export async function getSkill(id: string): Promise<Skill> {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}`, {
    headers: adminHeaders(),
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
    headers: adminHeaders(),
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
    headers: adminHeaders({ "If-Match": version }),
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
    headers: adminHeaders(),
  });
  if (res.status === 409) {
    let message = "Skill is referenced by a published scenario.";
    let impacted: string[] | undefined;
    try {
      const payload = await res.json();
      message = payload?.error || message;
      impacted = payload?.impactedIds;
    } catch (err) {
      // ignore parse failures
    }
    const error: any = new Error(message);
    error.code = "skill-conflict";
    if (impacted) {
      error.impactedIds = impacted;
    }
    throw error;
  }
  if (res.status !== 204 && res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete skill");
  }
}

export async function restoreSkill(id: string) {
  const res = await fetch(`${apiBase}/api/admin/skills/${id}/restore`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to restore skill");
  }
  return res.json();
}
