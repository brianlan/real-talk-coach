"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { listScenarios, deleteScenario, restoreScenario, publishScenario, unpublishScenario } from "@/services/api/admin/scenarios";

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listScenarios(true);
        setScenarios(data);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load scenarios");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const updateScenarioInList = (id: string, updates: any) => {
    setScenarios((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteScenario(id);
      updateScenarioInList(id, { recordStatus: "deleted" });
    } catch (err: any) {
      if (err?.message === "in-use") setError("Scenario has sessions and cannot be deleted.");
      else setError(err?.message ?? "Failed to delete scenario");
    }
  };

  const handleRestore = async (id: string) => {
    try {
      await restoreScenario(id);
      updateScenarioInList(id, { recordStatus: "active" });
    } catch (err: any) {
      setError(err?.message ?? "Failed to restore scenario");
    }
  };

  const handlePublish = async (id: string) => {
    try {
      const res = await publishScenario(id);
      updateScenarioInList(id, { status: res.status ?? "published" });
    } catch (err: any) {
      setError(err?.message ?? "Failed to publish scenario");
    }
  };

  const handleUnpublish = async (id: string) => {
    try {
      const res = await unpublishScenario(id);
      updateScenarioInList(id, { status: res.status ?? "draft" });
    } catch (err: any) {
      setError(err?.message ?? "Failed to unpublish scenario");
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Scenarios</h2>
          <p style={{ margin: 0, color: "#4a433b" }}>Create, publish, and manage scenarios.</p>
        </div>
        <Link
          href="/admin/scenarios/new"
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: "#2f2a24",
            color: "#f7f3ec",
            textDecoration: "none",
            fontWeight: 700,
          }}
        >
          New Scenario
        </Link>
      </div>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && scenarios.length === 0 ? <p>No scenarios yet.</p> : null}
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
        {scenarios.map((scenario) => (
          <li
            key={scenario.id}
            style={{
              border: "1px solid #e4ddd4",
              borderRadius: 12,
              padding: 12,
              background: scenario.recordStatus === "deleted" ? "#f6f0ea" : "#fff",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <div>
                <h3 style={{ margin: "0 0 4px" }}>{scenario.title}</h3>
                <p style={{ margin: 0, color: "#4a433b" }}>{scenario.category}</p>
                <p style={{ margin: "4px 0", color: "#4a433b" }}>Status: {scenario.status}</p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Link
                  href={`/admin/scenarios/${scenario.id}`}
                  style={{ padding: "8px 12px", border: "1px solid #d9d3cb", borderRadius: 8 }}
                >
                  Edit
                </Link>
                {scenario.status === "published" ? (
                  <button
                    type="button"
                    onClick={() => handleUnpublish(scenario.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
                  >
                    Unpublish
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handlePublish(scenario.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
                  >
                    Publish
                  </button>
                )}
                {scenario.recordStatus === "deleted" ? (
                  <button
                    type="button"
                    onClick={() => handleRestore(scenario.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #2f2a24" }}
                  >
                    Restore
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleDelete(scenario.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
