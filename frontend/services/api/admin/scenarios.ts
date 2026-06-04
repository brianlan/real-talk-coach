import { adminApiBase, adminHeaders } from "./client";

const apiBase = adminApiBase();

export type ScenarioInput = {
  metadata: {
    title: string;
    slug?: string;
    domain: string;
    scenarioType: string;
    difficulty: string;
    conflictLevel: string;
    estimatedDurationMinutes: number;
    tags: string[];
  };
  context: {
    situation: string;
    background: string;
    setting: string;
  };
  simulationConfig: {
    ai: {
      name: string;
      role: string;
      personality: string[];
      motivations: string[];
      constraints: string[];
      tendencies: string[];
      knowledge: string[];
      emotionalState: string;
    };
    trainee: {
      name: string;
      role: string;
      personality: string[];
      motivations: string[];
      constraints: string[];
      tendencies: string[];
      knowledge: string[];
      emotionalState: string;
    };
    language: string;
    conversationStart: {
      speakerRoleId: "ai" | "trainee";
      initialPromptToUser: string;
    };
    conversationRules: {
      stayInCharacter: boolean;
      allowNarration: boolean;
      coachingAllowed: boolean;
      tone: string;
    };
    conversationDynamics: {
      typicalBehaviors: string[];
      possibleResponses: string[];
    };
    decisionConstraints?: Record<string, unknown>;
    conversationEndConditions: {
      possibleEndStates: string[];
    };
  };
  evaluationConfig: {
    learningObjectives: string[];
    evaluationCriteria: {
      id: string;
      description: string;
    }[];
    skillsAssessed: string[];
    scoring: {
      scale: string;
      criteriaWeighting: Record<string, number>;
    };
    evaluationInstructionsForLLM: string;
  };
  status?: string;
};

export type Scenario = ScenarioInput & {
  id: string;
  recordStatus?: string;
  version?: string | null;
};

export async function listScenarios(includeDeleted = false): Promise<Scenario[]> {
  const res = await fetch(
    `${apiBase}/api/admin/scenarios?include_deleted=${includeDeleted ? "true" : "false"}`,
    { headers: adminHeaders() }
  );
  if (!res.ok) throw new Error("Failed to load scenarios");
  const body = await res.json();
  return body.scenarios ?? [];
}

export async function getScenario(id: string): Promise<Scenario> {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    headers: adminHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) throw new Error("Not found");
  if (!res.ok) throw new Error("Failed to load scenario");
  return res.json();
}

export async function createScenario(input: ScenarioInput) {
  const res = await fetch(`${apiBase}/api/admin/scenarios`, {
    method: "POST",
    headers: adminHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to create scenario");
  }
  return res.json();
}

export async function updateScenario(id: string, input: Partial<ScenarioInput>, version: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    method: "PUT",
    headers: adminHeaders({ "If-Match": version }),
    body: JSON.stringify(input),
  });
  if (res.status === 409) throw new Error("stale");
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Failed to update scenario");
  }
  return res.json();
}

export async function publishScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/publish`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to publish scenario");
  return res.json();
}

export async function unpublishScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/unpublish`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to unpublish scenario");
  return res.json();
}

export async function deleteScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });
  if (res.status === 409) {
    let message = "Scenario has sessions and cannot be deleted.";
    let impacted: string[] | undefined;
    try {
      const payload = await res.json();
      message = payload?.error || message;
      impacted = payload?.impactedIds;
    } catch (err) {
      // ignore parse failures
    }
    const error: any = new Error(message);
    error.code = "scenario-conflict";
    if (impacted) {
      error.impactedIds = impacted;
    }
    throw error;
  }
  if (res.status !== 204 && res.status !== 200) {
    const detail = await res.text();
    throw new Error(detail || "Failed to delete scenario");
  }
}

export async function restoreScenario(id: string) {
  const res = await fetch(`${apiBase}/api/admin/scenarios/${id}/restore`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to restore scenario");
  return res.json();
}
