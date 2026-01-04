"use client";

import { useEffect, useState } from "react";

import { createScenario, updateScenario, ScenarioInput } from "@/services/api/admin/scenarios";
import { listSkills, Skill } from "@/services/api/admin/skills";

export function ScenarioForm({
  scenarioId,
  initialValues,
  version,
  onSaved,
}: {
  scenarioId?: string;
  initialValues?: Partial<ScenarioInput>;
  version?: string | null;
  onSaved?: () => void;
}) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [values, setValues] = useState<ScenarioInput>({
    category: initialValues?.category ?? "",
    title: initialValues?.title ?? "",
    description: initialValues?.description ?? "",
    objective: initialValues?.objective ?? "",
    aiPersona:
      initialValues?.aiPersona ?? ({ name: "", role: "", background: "" } as ScenarioInput["aiPersona"]),
    traineePersona:
      initialValues?.traineePersona ?? ({ name: "", role: "", background: "" } as ScenarioInput["traineePersona"]),
    endCriteria: initialValues?.endCriteria ?? [""],
    skills: initialValues?.skills ?? [],
    prompt: initialValues?.prompt ?? "",
    idleLimitSeconds: initialValues?.idleLimitSeconds,
    durationLimitSeconds: initialValues?.durationLimitSeconds,
    status: initialValues?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    listSkills().then(setSkills).catch(() => setError("Failed to load skills"));
  }, []);

  const handleChange = (field: keyof ScenarioInput) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = e.target.value;
      setValues((prev) => ({ ...prev, [field]: value }));
    };

  const handlePersonaChange = (key: "aiPersona" | "traineePersona", field: "name" | "role" | "background") =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setValues((prev) => ({
        ...prev,
        [key]: { ...prev[key], [field]: value },
      }));
    };

  const handleSkillToggle = (skillId: string) => {
    setValues((prev) => {
      const exists = prev.skills.includes(skillId);
      return { ...prev, skills: exists ? prev.skills.filter((s) => s !== skillId) : [...prev.skills, skillId] };
    });
  };

  const handleEndCriteriaChange = (index: number, value: string) => {
    setValues((prev) => {
      const next = [...prev.endCriteria];
      next[index] = value;
      return { ...prev, endCriteria: next };
    });
  };

  const addEndCriteria = () => setValues((prev) => ({ ...prev, endCriteria: [...prev.endCriteria, ""] }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (scenarioId) {
        await updateScenario(scenarioId, values, version ?? "");
        setNotice("Saved");
      } else {
        await createScenario(values);
        setNotice("Created");
      }
      onSaved?.();
    } catch (err: any) {
      if (err?.message === "stale") setError("This scenario was updated elsewhere. Refresh and retry.");
      else setError(err?.message ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12, maxWidth: 800 }}>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Title</span>
        <input required value={values.title} onChange={handleChange("title")} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }} />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Category</span>
        <input required value={values.category} onChange={handleChange("category")} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb" }} />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Description</span>
        <textarea required value={values.description} onChange={handleChange("description")} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 100 }} />
      </label>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Objective</span>
        <textarea required value={values.objective} onChange={handleChange("objective")} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 80 }} />
      </label>

      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>AI Persona</strong>
        <input placeholder="Name" value={values.aiPersona.name} onChange={handlePersonaChange("aiPersona", "name")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        <input placeholder="Role" value={values.aiPersona.role} onChange={handlePersonaChange("aiPersona", "role")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        <input placeholder="Background" value={values.aiPersona.background} onChange={handlePersonaChange("aiPersona", "background")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
      </div>

      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>Trainee Persona</strong>
        <input placeholder="Name" value={values.traineePersona.name} onChange={handlePersonaChange("traineePersona", "name")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        <input placeholder="Role" value={values.traineePersona.role} onChange={handlePersonaChange("traineePersona", "role")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        <input placeholder="Background" value={values.traineePersona.background} onChange={handlePersonaChange("traineePersona", "background")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
      </div>

      <div style={{ display: "grid", gap: 6 }}>
        <strong>End Criteria</strong>
        {values.endCriteria.map((item, idx) => (
          <input
            key={idx}
            value={item}
            onChange={(e) => handleEndCriteriaChange(idx, e.target.value)}
            style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }}
          />
        ))}
        <button type="button" onClick={addEndCriteria} style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #d9d3cb", width: "fit-content" }}>
          Add End Criterion
        </button>
      </div>

      <div style={{ display: "grid", gap: 6 }}>
        <strong>Skills</strong>
        {skills.map((skill) => {
          const checked = values.skills.includes(skill.id);
          return (
            <label key={skill.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={checked}
                onChange={() => handleSkillToggle(skill.id)}
              />
              <span>{skill.name}</span>
            </label>
          );
        })}
        {skills.length === 0 ? <p style={{ color: "#4a433b" }}>No skills available.</p> : null}
      </div>

      <label style={{ display: "grid", gap: 6 }}>
        <span>Prompt</span>
        <textarea required value={values.prompt} onChange={handleChange("prompt")} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 80 }} />
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
