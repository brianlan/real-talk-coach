"use client";

import { useState } from "react";

import { SkillForm } from "@/components/admin/SkillForm";

export default function NewSkillPage() {
  const [message, setMessage] = useState<string | null>(null);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>New Skill</h2>
      <SkillForm onSaved={() => setMessage("Created")} />
      {message ? <p style={{ color: "#1f7a3d" }}>{message}</p> : null}
    </div>
  );
}
