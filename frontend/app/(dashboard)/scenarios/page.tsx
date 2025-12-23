import Link from "next/link";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function fetchScenarios(params: {
  search?: string;
  category?: string;
}) {
  const query = new URLSearchParams({ historyStepCount: "1" });
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.category) {
    query.set("category", params.category);
  }
  const response = await fetch(`${apiBase}/api/scenarios?${query}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  const data = await response.json();
  return data.items ?? [];
}

async function fetchSkills() {
  const response = await fetch(`${apiBase}/api/skills`, { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const data = await response.json();
  return data.items ?? [];
}

export default async function ScenariosPage({
  searchParams,
}: {
  searchParams?: { search?: string; category?: string };
}) {
  const [scenarios, skills] = await Promise.all([
    fetchScenarios({
      search: searchParams?.search,
      category: searchParams?.category,
    }),
    fetchSkills(),
  ]);

  const skillMap = new Map(skills.map((skill: any) => [skill.id, skill]));
  const categories = Array.from(
    new Set(scenarios.map((scenario: any) => scenario.category))
  );

  return (
    <main style={{ padding: "48px 24px" }}>
      <section style={{ maxWidth: 960, margin: "0 auto" }}>
        <header style={{ marginBottom: 24 }}>
          <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
            Practice Catalog
          </p>
          <h1 style={{ fontSize: 42, margin: "8px 0" }}>
            Choose your next conversation.
          </h1>
          <p style={{ maxWidth: 560, lineHeight: 1.5 }}>
            Browse live scenarios, see the focus skills, and jump into practice.
          </p>
        </header>

        <form
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            marginBottom: 32,
          }}
        >
          <input
            type="search"
            name="search"
            defaultValue={searchParams?.search ?? ""}
            placeholder="Search by title or objective"
            style={{
              flex: "1 1 240px",
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #d9cfc2",
              background: "rgba(255,255,255,0.9)",
            }}
          />
          <select
            name="category"
            defaultValue={searchParams?.category ?? ""}
            style={{
              minWidth: 180,
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #d9cfc2",
              background: "rgba(255,255,255,0.9)",
            }}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <button
            type="submit"
            style={{
              padding: "10px 18px",
              borderRadius: 999,
              border: "none",
              background: "#2f2a24",
              color: "#f7f0e6",
              cursor: "pointer",
            }}
          >
            Filter
          </button>
        </form>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
          }}
        >
          {scenarios.length === 0 ? (
            <div
              style={{
                border: "1px solid #e0d7cb",
                borderRadius: 16,
                padding: 24,
                background: "rgba(255,255,255,0.7)",
              }}
            >
              <p>No scenarios yet. Seed data to get started.</p>
            </div>
          ) : (
            scenarios.map((scenario: any) => (
              <Link
                key={scenario.id}
                href={`/scenarios/${scenario.id}`}
                style={{
                  textDecoration: "none",
                  color: "inherit",
                  border: "1px solid #e0d7cb",
                  borderRadius: 20,
                  padding: 24,
                  background: "rgba(255,255,255,0.85)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div style={{ fontSize: 12, letterSpacing: 1.5 }}>
                  {scenario.category}
                </div>
                <h2 style={{ margin: 0, fontSize: 24 }}>{scenario.title}</h2>
                <p style={{ margin: 0, lineHeight: 1.5 }}>{scenario.objective}</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {(scenario.skills ?? []).map((skillId: string) => {
                    const skill = skillMap.get(skillId);
                    return (
                      <span
                        key={skillId}
                        style={{
                          fontSize: 12,
                          padding: "4px 8px",
                          borderRadius: 999,
                          background: "#f2e8dd",
                        }}
                      >
                        {skill?.name ?? "Skill"}
                      </span>
                    );
                  })}
                </div>
              </Link>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
