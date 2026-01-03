"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ScenarioForm } from "@/components/admin/ScenarioForm";
import { getScenario } from "@/services/api/admin/scenarios";

export default function EditScenarioPage() {
  const params = useParams();
  const scenarioId = params?.scenarioId as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [initial, setInitial] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getScenario(scenarioId);
        setInitial(data);
        setVersion(data.version ?? null);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load scenario");
      } finally {
        setLoading(false);
      }
    };
    if (scenarioId) load();
  }, [scenarioId]);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>Edit Scenario</h2>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {!loading && !error && initial ? (
        <ScenarioForm
          scenarioId={scenarioId}
          initialValues={initial}
          version={version}
          onSaved={() => setError(null)}
        />
      ) : null}
    </div>
  );
}
