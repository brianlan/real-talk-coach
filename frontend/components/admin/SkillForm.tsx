"use client";

import { useState } from "react";

import { createSkill, updateSkill } from "@/services/api/admin/skills";

export type SkillFormValues = {
  name: string;
  category: string;
  rubric: string;
  description?: string | null;
};

export function SkillForm({
  initialValues,
  skillId,
  version,
  onSaved,
}: {
  initialValues?: SkillFormValues;
  skillId?: string;
  version?: string | null;
  onSaved?: (message: string) => void;
}) {
  const [values, setValues] = useState<SkillFormValues>(
    initialValues ?? { name: "", category: "", rubric: "", description: "" }
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleChange = (field: keyof SkillFormValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((prev) => ({ ...prev, [field]: e.target.value }));
    };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (skillId) {
        await updateSkill(skillId, values, version ?? "");
        setNotice("Saved");
      } else {
        await createSkill(values);
        setNotice("Created");
        setValues({ name: "", category: "", rubric: "", description: "" });
      }
      onSaved?.("saved");
    } catch (err: any) {
      if (err?.message === "stale") {
        setError("This skill was updated elsewhere. Refresh and retry.");
      } else {
        setError(err?.message ?? "Failed to save");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12, maxWidth: 640 }}>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Name</span>
        <input
          required
          value={values.name}
          onChange={handleChange("name")}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
        />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Category</span>
        <input
          required
          value={values.category}
          onChange={handleChange("category")}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }}
        />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Rubric</span>
        <textarea
          required
          value={values.rubric}
          onChange={handleChange("rubric")}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 120 }}
        />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Description (optional)</span>
        <textarea
          value={values.description ?? ""}
          onChange={handleChange("description")}
          style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 80 }}
        />
      </label>
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {notice ? <p style={{ color: "#1f7a3d" }}>{notice}</p> : null}
      <button
        type="submit"
        disabled={saving}
        style={{
          padding: "10px 16px",
          borderRadius: 10,
          border: "none",
          background: "#2f2a24",
          color: "#f7f3ec",
          cursor: "pointer",
          fontWeight: 700,
        }}
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </form>
  );
}
