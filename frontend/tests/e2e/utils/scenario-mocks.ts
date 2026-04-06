import type { Page } from "@playwright/test";

export type ScenarioMock = {
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
  status?: string;
};

export async function mockScenarioApi(
  page: Page,
  scenarios: ScenarioMock[]
) {
  await page.route("**/api/scenarios**", async (route) => {
    const url = route.request().url();
    const isDetail = url.includes("/api/scenarios/");
    if (isDetail) {
      const id = url.split("/api/scenarios/")[1]?.split("?")[0] ?? "";
      const scenario = scenarios.find((item) => item.id === id);
      if (!scenario) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "not found" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scenario),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: scenarios }),
    });
  });
}
