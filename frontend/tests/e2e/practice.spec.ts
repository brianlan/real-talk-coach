import { expect, test, type Page } from "@playwright/test";
import { mockScenarioApi } from "./utils/scenario-mocks";

async function mockPracticeApis(page: Page, sessionId: string) {
  await mockScenarioApi(page, [
    {
      id: "scenario-1",
      metadata: {
        domain: "Difficult Feedback",
        title: "Give constructive feedback to a peer",
        slug: "constructive-feedback",
        scenarioType: "practice",
        difficulty: "medium",
        conflictLevel: "medium",
        estimatedDurationMinutes: 5,
        tags: ["feedback"],
      },
      context: {
        situation: "Objective",
        background: "Test context",
        setting: "Office",
      },
      simulationConfig: {
        ai: {
          name: "Alex",
          role: "PM",
          personality: ["direct"],
          motivations: ["launch fast"],
          constraints: ["budget"],
          tendencies: ["interrupts"],
          knowledge: ["project details"],
          emotionalState: "stressed",
        },
        trainee: {
          name: "You",
          role: "Lead",
          personality: ["calm"],
          motivations: ["quality"],
          constraints: ["time"],
          tendencies: ["listens"],
          knowledge: ["tech"],
          emotionalState: "neutral",
        },
        language: "en",
        conversationStart: {
          speakerRoleId: "ai",
          initialPromptToUser: "Hello",
        },
        conversationRules: {
          stayInCharacter: true,
          allowNarration: false,
          coachingAllowed: false,
          tone: "professional",
        },
        conversationDynamics: {
          typicalBehaviors: ["fast talker"],
          possibleResponses: ["agrees", "disagrees"],
        },
        decisionConstraints: {
          maxRaiseWithoutHigherApprovalPercent: 10,
          alternativeOptions: ["delay"],
        },
        conversationEndConditions: {
          possibleEndStates: ["End"],
        },
      },
      evaluationConfig: {
        learningObjectives: [],
        evaluationCriteria: [],
        skillsAssessed: [],
        scoring: { scale: "1-5", criteriaWeighting: {} },
        evaluationInstructionsForLLM: "Evaluate",
      },
    },
  ]);

  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: sessionId }),
    });
  });

  await page.route("**/api/realtime/token", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "test-token",
        room_id: "room-1",
        app_id: "test-app-id",
      }),
    });
  });
}

test("practice flow starts a session from scenario list", async ({ page }) => {
  await mockPracticeApis(page, "session-1");

  await page.goto("/practice");
  await expect(page.getByText("Give constructive feedback to a peer")).toBeVisible();

  await page.getByRole("button", { name: "Start Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/practice\/session-1/);
});

test("start practice sends the selected scenario id", async ({ page }) => {
  let requestBody: Record<string, unknown> | null = null;

  await mockScenarioApi(page, [
    {
      id: "scenario-1",
      metadata: {
        domain: "Difficult Feedback",
        title: "Give constructive feedback to a peer",
        slug: "constructive-feedback",
        scenarioType: "practice",
        difficulty: "medium",
        conflictLevel: "medium",
        estimatedDurationMinutes: 5,
        tags: ["feedback"],
      },
      context: {
        situation: "Objective",
        background: "Test context",
        setting: "Office",
      },
      simulationConfig: {
        ai: {
          name: "Alex",
          role: "PM",
          personality: ["direct"],
          motivations: ["launch fast"],
          constraints: ["budget"],
          tendencies: ["interrupts"],
          knowledge: ["project details"],
          emotionalState: "stressed",
        },
        trainee: {
          name: "You",
          role: "Lead",
          personality: ["calm"],
          motivations: ["quality"],
          constraints: ["time"],
          tendencies: ["listens"],
          knowledge: ["tech"],
          emotionalState: "neutral",
        },
        language: "en",
        conversationStart: {
          speakerRoleId: "ai",
          initialPromptToUser: "Hello",
        },
        conversationRules: {
          stayInCharacter: true,
          allowNarration: false,
          coachingAllowed: false,
          tone: "professional",
        },
        conversationDynamics: {
          typicalBehaviors: ["fast talker"],
          possibleResponses: ["agrees", "disagrees"],
        },
        decisionConstraints: {
          maxRaiseWithoutHigherApprovalPercent: 10,
          alternativeOptions: ["delay"],
        },
        conversationEndConditions: {
          possibleEndStates: ["End"],
        },
      },
      evaluationConfig: {
        learningObjectives: [],
        evaluationCriteria: [],
        skillsAssessed: [],
        scoring: { scale: "1-5", criteriaWeighting: {} },
        evaluationInstructionsForLLM: "Evaluate",
      },
    },
  ]);

  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    requestBody = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "session-2" }),
    });
  });

  await page.route("**/api/realtime/token", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "test-token",
        room_id: "room-1",
        app_id: "test-app-id",
      }),
    });
  });

  await page.goto("/practice");
  await page.getByRole("button", { name: "Start Practice", exact: true }).click();

  await expect(page).toHaveURL(/\/practice\/session-2/);
  await expect.poll(() => requestBody?.scenarioId).toBe("scenario-1");
});
