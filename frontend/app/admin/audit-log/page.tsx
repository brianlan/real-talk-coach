"use client";

import { useEffect, useState } from "react";

import { AuditLogEntry, listAuditLog } from "@/services/api/admin/audit-log";

const defaultFilters = {
  entityType: "",
  adminId: "",
  startDate: "",
  endDate: "",
};

function formatTimestamp(value?: string | null) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (err) {
    return value;
  }
}

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [filters, setFilters] = useState(defaultFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (nextFilters = filters) => {
    setLoading(true);
    setError(null);
    try {
      const normalized = {
        entityType: nextFilters.entityType || undefined,
        adminId: nextFilters.adminId || undefined,
        startDate: nextFilters.startDate || undefined,
        endDate: nextFilters.endDate || undefined,
      };
      const data = await listAuditLog(normalized);
      setEntries(data);
    } catch (err: any) {
      setError(err?.message ?? "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (field: keyof typeof filters) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = e.target.value;
      setFilters((prev) => ({ ...prev, [field]: value }));
    };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    load(filters);
  };

  const handleReset = () => {
    setFilters(defaultFilters);
    load(defaultFilters);
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Audit Log</h2>
          <p style={{ margin: 0, color: "#4a433b" }}>
            Track recent admin actions across skills, scenarios, and sessions.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{ display: "grid", gap: 12, border: "1px solid #e4ddd4", borderRadius: 12, padding: 16 }}
      >
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Entity</span>
            <select
              value={filters.entityType}
              onChange={handleChange("entityType")}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
            >
              <option value="">All</option>
              <option value="skill">Skills</option>
              <option value="scenario">Scenarios</option>
              <option value="session">Sessions</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Admin ID</span>
            <input
              value={filters.adminId}
              onChange={handleChange("adminId")}
              placeholder="token or user id"
              style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Start</span>
            <input
              type="datetime-local"
              value={filters.startDate}
              onChange={handleChange("startDate")}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>End</span>
            <input
              type="datetime-local"
              value={filters.endDate}
              onChange={handleChange("endDate")}
              style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="submit"
            style={{
              padding: "10px 16px",
              borderRadius: 10,
              border: "none",
              background: "#2f2a24",
              color: "#f7f3ec",
              fontWeight: 700,
            }}
          >
            Apply Filters
          </button>
          <button
            type="button"
            onClick={handleReset}
            style={{
              padding: "10px 16px",
              borderRadius: 10,
              border: "1px solid #d9d3cb",
              background: "transparent",
            }}
          >
            Reset
          </button>
        </div>
      </form>

      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && entries.length === 0 ? <p>No audit entries found.</p> : null}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #e4ddd4" }}>
              <th style={{ padding: "8px 4px" }}>Timestamp</th>
              <th style={{ padding: "8px 4px" }}>Admin</th>
              <th style={{ padding: "8px 4px" }}>Action</th>
              <th style={{ padding: "8px 4px" }}>Entity</th>
              <th style={{ padding: "8px 4px" }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id} style={{ borderBottom: "1px solid #f0e9df" }}>
                <td style={{ padding: "10px 4px", whiteSpace: "nowrap" }}>{formatTimestamp(entry.timestamp)}</td>
                <td style={{ padding: "10px 4px" }}>{entry.adminId}</td>
                <td style={{ padding: "10px 4px" }}>{entry.action}</td>
                <td style={{ padding: "10px 4px" }}>
                  <div style={{ display: "grid" }}>
                    <strong style={{ textTransform: "capitalize" }}>{entry.entityType}</strong>
                    <span style={{ color: "#4a433b", fontSize: 12 }}>{entry.entityId}</span>
                  </div>
                </td>
                <td style={{ padding: "10px 4px" }}>{entry.details ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
