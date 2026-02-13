import { getApiBase } from "../base";

const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "";

export function adminApiBase(): string {
  return getApiBase();
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
  if (path.startsWith("/")) return `${getApiBase()}${path}`;
  return `${getApiBase()}/${path}`;
}
