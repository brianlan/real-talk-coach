import { redirect } from "next/navigation";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function fetchScenario(scenarioId: string) {
  const response = await fetch(
    `${apiBase}/api/scenarios/${scenarioId}?historyStepCount=1`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    return null;
  }
  return response.json();
}

async function createSession(scenarioId: string) {
  const response = await fetch(`${apiBase}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenarioId,
      clientSessionStartedAt: new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export default async function ScenarioDetailPage({
  params,
}: {
  params: Promise<{ scenarioId: string }>;
}) {
  const resolvedParams = await params;
  const scenario = await fetchScenario(resolvedParams.scenarioId);
  if (!scenario) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>Scenario not found.</p>
      </main>
    );
  }

  async function startPractice() {
    "use server";
    const session = await createSession(resolvedParams.scenarioId);
    if (!session?.id) {
      redirect("/scenarios");
    }
    redirect(`/practice/${session.id}`);
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
            {(scenario.endCriteria ?? []).map((item: string) => (
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

        <form action={startPractice} style={{ marginTop: 32 }}>
          <button
            type="submit"
            style={{
              padding: "14px 28px",
              borderRadius: 999,
              border: "none",
              background: "#2f2a24",
              color: "#f7f0e6",
              fontSize: 16,
              cursor: "pointer",
            }}
          >
            Start practice
          </button>
        </form>
      </section>
    </main>
  );
}
