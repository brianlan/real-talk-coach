"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { fetchHistoryList, SessionPage } from "@/services/api/history";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Scenario = {
  id: string;
  category?: string;
  title?: string;
  objective?: string;
};

async function fetchScenario(scenarioId: string): Promise<Scenario | null> {
  const response = await fetch(`${apiBase}/api/scenarios/${scenarioId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export default function HistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [history, setHistory] = useState<SessionPage | null>(null);
  const [scenarioMap, setScenarioMap] = useState<Map<string, Scenario>>(new Map());
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const search = searchParams.get("search") ?? "";
  const category = searchParams.get("category") ?? "";
  const sort = (searchParams.get("sort") as "startedAtDesc" | "startedAtAsc" | null) ??
    "startedAtDesc";

  useEffect(() => {
    let canceled = false;
    const loadHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const next = await fetchHistoryList({
          historyStepCount: 1,
          page: 1,
          pageSize: 20,
          search: search || undefined,
          category: category || undefined,
          sort: sort || undefined,
        });
        if (canceled) {
          return;
        }
        setHistory(next);
        const scenarioIds = Array.from(
          new Set(next.items.map((item) => item.scenarioId))
        );
        const scenarios = await Promise.all(
          scenarioIds.map((scenarioId) => fetchScenario(scenarioId))
        );
        if (canceled) {
          return;
        }
        const map = new Map(
          scenarios
            .filter(Boolean)
            .map((scenario) => [scenario!.id, scenario as Scenario])
        );
        setScenarioMap(map);
        setCategories(
          Array.from(
            new Set(
              scenarios
                .filter(Boolean)
                .map((scenario) => scenario!.category)
                .filter(Boolean) as string[]
            )
          )
        );
      } catch (err) {
        if (!canceled) {
          setError((err as Error).message);
        }
      } finally {
        if (!canceled) {
          setLoading(false);
        }
      }
    };

    loadHistory();
    return () => {
      canceled = true;
    };
  }, [search, category, sort]);

  const formKey = useMemo(
    () => `${search}|${category}|${sort}`,
    [search, category, sort]
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const nextQuery = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      if (value) {
        nextQuery.set(key, String(value));
      }
    }
    const queryString = nextQuery.toString();
    router.push(queryString ? `/history?${queryString}` : "/history");
  };

  return (
    <main style={{ padding: "48px 24px" }}>
      <section style={{ maxWidth: 960, margin: "0 auto" }}>
        <header style={{ marginBottom: 24 }}>
          <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
            History
          </p>
          <h1 style={{ fontSize: 42, margin: "8px 0" }}>Review past sessions.</h1>
          <p style={{ maxWidth: 560, lineHeight: 1.5 }}>
            Revisit transcripts, replay audio, and practice again with fresh runs.
          </p>
        </header>

        <form
          key={formKey}
          onSubmit={handleSubmit}
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
            defaultValue={search}
            placeholder="Search by scenario title or objective"
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
            defaultValue={category}
            style={{
              minWidth: 180,
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #d9cfc2",
              background: "rgba(255,255,255,0.9)",
            }}
          >
            <option value="">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            name="sort"
            defaultValue={sort}
            style={{
              minWidth: 180,
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #d9cfc2",
              background: "rgba(255,255,255,0.9)",
            }}
          >
            <option value="startedAtDesc">Newest first</option>
            <option value="startedAtAsc">Oldest first</option>
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

        {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
          }}
        >
          {loading ? (
            <div
              style={{
                border: "1px solid #e0d7cb",
                borderRadius: 16,
                padding: 24,
                background: "rgba(255,255,255,0.7)",
              }}
            >
              <p>Loading history...</p>
            </div>
          ) : history?.items.length === 0 ? (
            <div
              style={{
                border: "1px solid #e0d7cb",
                borderRadius: 16,
                padding: 24,
                background: "rgba(255,255,255,0.7)",
              }}
            >
              <p>No sessions yet. Start a practice session to see history.</p>
            </div>
          ) : (
            history?.items.map((item) => {
              const scenario = scenarioMap.get(item.scenarioId);
              return (
                <Link
                  key={item.id}
                  href={`/history/${item.id}`}
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
                    {scenario?.category ?? "Session"}
                  </div>
                  <h2 style={{ margin: 0, fontSize: 22 }}>
                    {scenario?.title ?? item.scenarioId}
                  </h2>
                  <p style={{ margin: 0 }}>
                    {scenario?.objective ?? "Review session details."}
                  </p>
                  <p style={{ margin: 0, color: "#6a5f54", fontSize: 12 }}>
                    {item.startedAt
                      ? `Started ${new Date(item.startedAt).toLocaleString()}`
                      : "Start time unavailable"}
                  </p>
                </Link>
              );
            })
          )}
        </div>
      </section>
    </main>
  );
}
