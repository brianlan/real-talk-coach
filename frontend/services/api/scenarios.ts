import { getApiBase } from "./base";

const apiBase = getApiBase();

export type Scenario = {
  id: string;
  category: string;
  title: string;
  description: string;
  objective: string;
  aiPersona: { name: string; role: string; background: string };
  traineePersona: { name: string; role: string; background: string };
  endCriteria: string[];
  skills: string[];
  skillSummaries?: {
    skillId: string;
    name: string;
    rubric: string;
  }[];
  idleLimitSeconds?: number;
  durationLimitSeconds?: number;
  prompt?: string;
};

export async function getScenarios(category?: string): Promise<Scenario[]> {
  const params = new URLSearchParams();
  if (category) {
    params.set("category", category);
  }
  
  const res = await fetch(`${apiBase}/api/scenarios?${params.toString()}`, {
    cache: "no-store",
  });
  
  if (!res.ok) {
    throw new Error("Failed to load scenarios");
  }
  
  const body = await res.json();
  return body.items ?? [];
}
