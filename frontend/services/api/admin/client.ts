const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

export function adminApiBase(): string {
  return API_BASE;
}

export function adminHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(ADMIN_TOKEN ? { "X-Admin-Token": ADMIN_TOKEN } : {}),
    ...(extra ?? {}),
  };
}

export function adminUrl(path: string): string {
  if (path.startsWith("http")) return path;
  if (path.startsWith("/")) return `${API_BASE}${path}`;
  return `${API_BASE}/${path}`;
}
