import { adminApiBase, adminHeaders } from "./client";

const apiBase = adminApiBase();

export type AuditLogFilters = {
  entityType?: string | null;
  adminId?: string | null;
  startDate?: string | null;
  endDate?: string | null;
};

export type AuditLogEntry = {
  id: string;
  adminId: string;
  action: string;
  entityType: string;
  entityId: string;
  timestamp?: string | null;
  details?: string | null;
};

export function buildAuditLogQuery(filters: AuditLogFilters = {}): string {
  const params = new URLSearchParams();
  const { entityType, adminId, startDate, endDate } = filters;
  if (entityType) params.set("entityType", entityType);
  if (adminId) params.set("adminId", adminId);
  if (startDate) params.set("startDate", startDate);
  if (endDate) params.set("endDate", endDate);
  return params.toString();
}

export async function listAuditLog(filters: AuditLogFilters = {}): Promise<AuditLogEntry[]> {
  const query = buildAuditLogQuery(filters);
  const url = query ? `${apiBase}/api/admin/audit-log?${query}` : `${apiBase}/api/admin/audit-log`;
  const res = await fetch(url, {
    headers: adminHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("Failed to load audit log");
  }
  const body = await res.json();
  return body.entries ?? [];
}
