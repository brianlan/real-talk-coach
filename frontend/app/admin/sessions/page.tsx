"use client";

import { useEffect, useState } from "react";

import { listSessions, deleteSession } from "@/services/api/admin/sessions";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listSessions();
        setSessions(data);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      setError(err?.message ?? "Failed to delete session");
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>Sessions</h2>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && sessions.length === 0 ? <p>No sessions found.</p> : null}
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
        {sessions.map((session) => (
          <li
            key={session.id}
            style={{
              border: "1px solid #e4ddd4",
              borderRadius: 12,
              padding: 12,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: "0 0 4px" }}>{session.id}</h3>
                <p style={{ margin: 0, color: "#4a433b" }}>Scenario: {session.scenarioId}</p>
                <p style={{ margin: 0, color: "#4a433b" }}>Status: {session.status}</p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => handleDelete(session.id)}
                  style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
                >
                  Delete
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
