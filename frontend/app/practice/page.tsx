"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { getScenarios } from "@/services/api/scenarios";
import { createSession } from "@/services/api/sessions";

export default function PracticePage() {
  const router = useRouter();
  
  const { data: scenarios, isLoading } = useQuery({
    queryKey: ["scenarios"],
    queryFn: () => getScenarios(),
  });

  const createSessionMutation = useMutation({
    mutationFn: createSession,
    onSuccess: (data) => {
      router.push(`/practice/${data.id}`);
    },
  });

  const handleStartPractice = (scenarioId: string) => {
    createSessionMutation.mutate({
      scenarioId,
      clientSessionStartedAt: new Date().toISOString(),
    });
  };

  if (isLoading) {
    return (
      <div style={{ padding: 48, textAlign: "center", color: "#666" }}>
        Loading scenarios...
      </div>
    );
  }

  return (
    <div style={{ padding: "48px 64px" }}>
      <header style={{ marginBottom: 48, maxWidth: 600 }}>
        <h1 style={{ fontSize: 36, marginBottom: 16, color: "#2f2a24" }}>Select a Scenario</h1>
        <p style={{ fontSize: 18, color: "#6b6054", lineHeight: 1.5 }}>
          Choose a scenario to begin your practice session. Each scenario is designed to target specific communication skills.
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 24,
        }}
      >
        {scenarios?.map((scenario) => (
          <div
            key={scenario.id}
            style={{
              padding: 24,
              background: "#fff",
              borderRadius: 16,
              border: "1px solid #e0d7cb",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              transition: "transform 0.2s, box-shadow 0.2s",
              cursor: "pointer",
            }}
            onClick={() => handleStartPractice(scenario.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                handleStartPractice(scenario.id);
              }
            }}
          >
            <span
              style={{
                display: "inline-block",
                padding: "4px 8px",
                borderRadius: 4,
                background: "#f3eadf",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b6054",
                marginBottom: 12,
              }}
            >
              {scenario.category}
            </span>
            <h3 style={{ fontSize: 20, margin: "0 0 8px", color: "#2f2a24" }}>
              {scenario.title}
            </h3>
            <p style={{ margin: "0 0 24px", color: "#6b6054", fontSize: 14, flex: 1 }}>
              {scenario.description}
            </p>
            <button
              disabled={createSessionMutation.isPending}
              style={{
                padding: "8px 16px",
                borderRadius: 999,
                border: "none",
                background: "#2f2a24",
                color: "#f7f0e6",
                fontWeight: 500,
                cursor: "pointer",
                opacity: createSessionMutation.isPending ? 0.7 : 1,
              }}
            >
              {createSessionMutation.isPending ? "Starting..." : "Start Practice"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
