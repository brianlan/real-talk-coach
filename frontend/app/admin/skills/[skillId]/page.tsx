"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { SkillForm } from "@/components/admin/SkillForm";
import { getSkill } from "@/services/api/admin/skills";

export default function EditSkillPage() {
  const params = useParams();
  const skillId = params?.skillId as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [initial, setInitial] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getSkill(skillId);
        setInitial({
          name: data.name,
          category: data.category,
          rubric: data.rubric,
          description: data.description ?? "",
        });
        setVersion(data.version ?? null);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load skill");
      } finally {
        setLoading(false);
      }
    };
    if (skillId) {
      load();
    }
  }, [skillId]);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>Edit Skill</h2>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && !error && initial ? (
        <SkillForm
          skillId={skillId}
          initialValues={initial}
          version={version}
          onSaved={() => setError(null)}
        />
      ) : null}
    </div>
  );
}
