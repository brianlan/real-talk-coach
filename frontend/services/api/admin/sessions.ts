const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const adminToken = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

function authHeaders(extra?: Record<string, string>) {
  return {
    "Content-Type": "application/json",
    ...(adminToken ? { "X-Admin-Token": adminToken } : {}),
    ...(extra ?? {}),
  } as Record<string, string>;
}

export async function listSessions() {
  const res = await fetch(`${apiBase}/api/admin/sessions`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load sessions");
  const body = await res.json();
  return body.sessions ?? [];
}

export async function getSession(id: string) {
  const res = await fetch(`${apiBase}/api/admin/sessions/${id}`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) throw new Error("Not found");
  if (!res.ok) throw new Error("Failed to load session");
  return res.json();
}

export async function deleteSession(id: string) {
  const res = await fetch(`${apiBase}/api/admin/sessions/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status !== 204 && res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete session");
  }
}
