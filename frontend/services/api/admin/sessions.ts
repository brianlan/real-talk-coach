import { adminApiBase, adminHeaders } from "./client";

const apiBase = adminApiBase();

export async function listSessions() {
  const res = await fetch(`${apiBase}/api/admin/sessions`, {
    headers: adminHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load sessions");
  const body = await res.json();
  return body.sessions ?? [];
}

export async function getSession(id: string) {
  const res = await fetch(`${apiBase}/api/admin/sessions/${id}`, {
    headers: adminHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) throw new Error("Not found");
  if (!res.ok) throw new Error("Failed to load session");
  return res.json();
}

export async function deleteSession(id: string) {
  const res = await fetch(`${apiBase}/api/admin/sessions/${id}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });
  if (res.status !== 204 && res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete session");
  }
}
