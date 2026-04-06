import { getApiBase } from "./base";

const apiBase = getApiBase();

export type Scenario = {
  id: string;
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
    decisionConstraints: {
      maxRaiseWithoutHigherApprovalPercent?: number;
      alternativeOptions: string[];
    };
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
