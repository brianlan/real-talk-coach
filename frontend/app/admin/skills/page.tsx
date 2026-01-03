"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { listSkills, deleteSkill, restoreSkill } from "@/services/api/admin/skills";

export default function SkillsPage() {
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listSkills(true);
        setSkills(data);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load skills");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteSkill(id);
      setSkills((prev) => prev.map((s) => (s.id === id ? { ...s, status: "deleted" } : s)));
    } catch (err: any) {
      setError(err?.message ?? "Failed to delete skill");
    }
  };

  const handleRestore = async (id: string) => {
    try {
      await restoreSkill(id);
      setSkills((prev) => prev.map((s) => (s.id === id ? { ...s, status: "active" } : s)));
    } catch (err: any) {
      setError(err?.message ?? "Failed to restore skill");
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Skills</h2>
          <p style={{ margin: 0, color: "#4a433b" }}>Manage reusable rubrics for scenarios.</p>
        </div>
        <Link
          href="/admin/skills/new"
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: "#2f2a24",
            color: "#f7f3ec",
            textDecoration: "none",
            fontWeight: 700,
          }}
        >
          New Skill
        </Link>
      </div>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && skills.length === 0 ? <p>No skills yet.</p> : null}
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
        {skills.map((skill) => (
          <li
            key={skill.id}
            style={{
              border: "1px solid #e4ddd4",
              borderRadius: 12,
              padding: 12,
              background: skill.status === "deleted" ? "#f6f0ea" : "#fff",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: "0 0 4px" }}>{skill.name}</h3>
                <p style={{ margin: 0, color: "#4a433b" }}>{skill.category}</p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Link
                  href={`/admin/skills/${skill.id}`}
                  style={{ padding: "8px 12px", border: "1px solid #d9d3cb", borderRadius: 8 }}
                >
                  Edit
                </Link>
                {skill.status === "deleted" ? (
                  <button
                    type="button"
                    onClick={() => handleRestore(skill.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #2f2a24" }}
                  >
                    Restore
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleDelete(skill.id)}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
            <p style={{ margin: "8px 0 0", color: "#4a433b" }}>{skill.rubric}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
