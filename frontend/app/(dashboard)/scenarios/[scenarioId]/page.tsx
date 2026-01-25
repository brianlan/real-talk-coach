"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Scenario = {
  id: string;
  category?: string;
  title?: string;
  description?: string;
  objective?: string;
  aiPersona?: { name?: string; background?: string };
  traineePersona?: { name?: string; background?: string };
  endCriteria?: string[];
};

type PracticeLanguage = "en" | "zh";

const detectScenarioLanguage = (scenario: Scenario | null): PracticeLanguage => {
  if (!scenario) {
    return "en";
  }
  const text = `${scenario.title ?? ""} ${scenario.description ?? ""} ${scenario.objective ?? ""}`;
  return /[\\u4e00-\\u9fff]/.test(text) ? "zh" : "en";
};

export default function ScenarioDetailPage() {
  const params = useParams<{ scenarioId: string }>();
  const router = useRouter();
  const scenarioId = params?.scenarioId;
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [language, setLanguage] = useState<PracticeLanguage | null>(null);

  useEffect(() => {
    let canceled = false;
    const loadScenario = async () => {
      if (!scenarioId) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${apiBase}/api/scenarios/${scenarioId}?historyStepCount=1`,
          { cache: "no-store" }
        );
        if (!response.ok) {
          throw new Error("Scenario not found.");
        }
        const data = (await response.json()) as Scenario;
        if (!canceled) {
          setScenario(data);
          setLanguage((prev) => prev ?? detectScenarioLanguage(data));
        }
      } catch (err) {
        if (!canceled) {
          setScenario(null);
          setError((err as Error).message);
        }
      } finally {
        if (!canceled) {
          setLoading(false);
        }
      }
    };
    loadScenario();
    return () => {
      canceled = true;
    };
  }, [scenarioId]);

  const startPractice = async () => {
    if (!scenarioId || starting) {
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const resolvedLanguage = language ?? detectScenarioLanguage(scenario);
      const response = await fetch(`${apiBase}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenarioId,
          clientSessionStartedAt: new Date().toISOString(),
          language: resolvedLanguage,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to start practice session.");
      }
      const session = await response.json();
      if (!session?.id) {
        throw new Error("Failed to start practice session.");
      }
      router.push(`/practice/${session.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>Loading scenario...</p>
      </main>
    );
  }

  if (!scenario) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>{error ?? "Scenario not found."}</p>
      </main>
    );
  }

  return (
    <main style={{ padding: "48px 24px" }}>
      <section style={{ maxWidth: 820, margin: "0 auto" }}>
        <header style={{ marginBottom: 24 }}>
          <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
            {scenario.category}
          </p>
          <h1 style={{ fontSize: 40, margin: "8px 0" }}>{scenario.title}</h1>
          <p style={{ lineHeight: 1.6 }}>{scenario.description}</p>
        </header>

        <div
          style={{
            borderRadius: 20,
            padding: 24,
            background: "rgba(255,255,255,0.85)",
            border: "1px solid #e0d7cb",
            marginBottom: 24,
          }}
        >
          <h2 style={{ marginTop: 0 }}>Objective</h2>
          <p>{scenario.objective}</p>
          <h3>End criteria</h3>
          <ul>
            {(scenario.endCriteria ?? []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div
            style={{
              flex: "1 1 280px",
              padding: 20,
              borderRadius: 16,
              background: "#f3eadf",
            }}
          >
            <h3 style={{ marginTop: 0 }}>AI Persona</h3>
            <p>{scenario.aiPersona?.name}</p>
            <p style={{ margin: 0 }}>{scenario.aiPersona?.background}</p>
          </div>
          <div
            style={{
              flex: "1 1 280px",
              padding: 20,
              borderRadius: 16,
              background: "#f3eadf",
            }}
          >
            <h3 style={{ marginTop: 0 }}>Your Persona</h3>
            <p>{scenario.traineePersona?.name}</p>
            <p style={{ margin: 0 }}>{scenario.traineePersona?.background}</p>
          </div>
        </div>

        <div style={{ marginTop: 32, display: "flex", gap: 16, flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "8px 12px",
              borderRadius: 999,
              border: "1px solid #e0d7cb",
              background: "#fffaf2",
            }}
          >
            <span style={{ fontSize: 13, letterSpacing: 0.5 }}>Practice language</span>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="radio"
                name="practice-language"
                value="zh"
                checked={(language ?? detectScenarioLanguage(scenario)) === "zh"}
                onChange={() => setLanguage("zh")}
              />
              中文
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="radio"
                name="practice-language"
                value="en"
                checked={(language ?? detectScenarioLanguage(scenario)) === "en"}
                onChange={() => setLanguage("en")}
              />
              English
            </label>
          </div>
          <button
            type="button"
            onClick={startPractice}
            disabled={starting}
            style={{
              padding: "14px 28px",
              borderRadius: 999,
              border: "none",
              background: "#2f2a24",
              color: "#f7f0e6",
              fontSize: 16,
              cursor: starting ? "not-allowed" : "pointer",
            }}
          >
            {starting ? "Starting..." : "Start practice"}
          </button>
          {error ? <p style={{ margin: 0, color: "#b24332" }}>{error}</p> : null}
        </div>
      </section>
    </main>
  );
}
