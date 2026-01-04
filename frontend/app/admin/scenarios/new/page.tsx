"use client";

import { ScenarioForm } from "@/components/admin/ScenarioForm";

export default function NewScenarioPage() {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>New Scenario</h2>
      <ScenarioForm onSaved={() => {}} />
    </div>
  );
}
