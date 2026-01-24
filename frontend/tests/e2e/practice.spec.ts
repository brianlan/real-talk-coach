import { test, expect } from "@playwright/test";
import { mockScenarioApi } from "./utils/scenario-mocks";

test("practice flow with mocked websocket events", async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      url: string;
      readyState = 1;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      private listeners: Record<string, Array<(event: any) => void>> = {};

      constructor(url: string) {
        this.url = url;
        (window as any).__lastWebSocket = this;
        setTimeout(() => this.onopen?.(new Event("open")), 0);
      }

      send() {}

      close() {
        this.readyState = 3;
        this.onclose?.(new CloseEvent("close"));
      }

      addEventListener(type: string, listener: (event: any) => void) {
        this.listeners[type] = this.listeners[type] ?? [];
        this.listeners[type].push(listener);
      }

      removeEventListener(type: string, listener: (event: any) => void) {
        this.listeners[type] = (this.listeners[type] ?? []).filter(
          (item) => item !== listener
        );
      }

      dispatchEvent(event: Event) {
        const listeners = this.listeners[event.type] ?? [];
        listeners.forEach((listener) => listener(event));
        return true;
      }

      emitMessage(payload: unknown) {
        const event = new MessageEvent("message", {
          data: JSON.stringify(payload),
        });
        this.onmessage?.(event);
        this.dispatchEvent(event);
      }
    }

    (window as any).WebSocket = MockWebSocket;
    (window as any).__emitWsMessage = (payload: unknown) => {
      const socket = (window as any).__lastWebSocket as MockWebSocket | undefined;
      socket?.emitMessage(payload);
    };
  });

  await mockScenarioApi(page, [
    {
      id: "scenario-1",
      category: "Difficult Feedback",
      title: "Give constructive feedback to a peer",
      description: "Scenario description",
      objective: "Objective",
      aiPersona: { name: "Alex", role: "PM", background: "Test" },
      traineePersona: { name: "You", role: "Lead", background: "Test" },
      endCriteria: ["End"],
      skills: [],
      skillSummaries: [],
      idleLimitSeconds: 8,
      durationLimitSeconds: 300,
      prompt: "Prompt",
    },
  ]);

  await page.route("**/api/skills", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });

  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "session-1",
        scenarioId: "scenario-1",
        stubUserId: "pilot-user",
        status: "pending",
        clientSessionStartedAt: "2025-01-01T00:00:00Z",
        startedAt: "2025-01-01T00:00:00Z",
        endedAt: null,
        totalDurationSeconds: null,
        idleLimitSeconds: 8,
        durationLimitSeconds: 300,
        wsChannel: "/ws/sessions/session-1",
        objectiveStatus: "unknown",
        objectiveReason: null,
        evaluationId: null,
      }),
    });
  });

  await page.route("**/api/sessions/session-1?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session: {
          id: "session-1",
          scenarioId: "scenario-1",
          stubUserId: "pilot-user",
          status: "active",
          terminationReason: null,
          clientSessionStartedAt: "2025-01-01T00:00:00Z",
          startedAt: "2025-01-01T00:00:00Z",
          endedAt: null,
          totalDurationSeconds: null,
          idleLimitSeconds: 8,
          durationLimitSeconds: 300,
          wsChannel: "/ws/sessions/session-1",
          objectiveStatus: "unknown",
          objectiveReason: null,
          evaluationId: null,
        },
        scenario: {
          id: "scenario-1",
          category: "Difficult Feedback",
          title: "Give constructive feedback to a peer",
          description: "Scenario description",
          objective: "Objective",
          aiPersona: { name: "Alex", role: "PM", background: "Test" },
          traineePersona: { name: "You", role: "Lead", background: "Test" },
          endCriteria: ["End"],
          skills: [],
          skillSummaries: [],
          idleLimitSeconds: 8,
          durationLimitSeconds: 300,
          prompt: "Prompt",
        },
        turns: [],
        evaluation: null,
      }),
    });
  });

  await page.route("**/api/sessions/session-1/evaluation", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not found" }),
    });
  });

  await page.goto("/scenarios/scenario-1");
  await expect(page.getByText("Give constructive feedback to a peer")).toBeVisible();

  await page.getByRole("button", { name: /start practice/i }).click();
  await page.waitForURL(/\/practice\/session-1/);
  await page.waitForFunction(
    () => (window as any).__lastWebSocket?.onmessage
  );

  await page.evaluate(() =>
    (window as any).__emitWsMessage({
      type: "ai_turn",
      turn: {
        id: "turn-0",
        sessionId: "session-1",
        sequence: 0,
        speaker: "ai",
        transcript: "Hello",
        audioFileId: "file-1",
        audioUrl: "https://example.com/audio.mp3",
        asrStatus: null,
        createdAt: "2025-01-01T00:00:00Z",
        startedAt: "2025-01-01T00:00:00Z",
        endedAt: "2025-01-01T00:00:00Z",
        context: null,
        latencyMs: 120,
      },
    })
  );

  await page.evaluate(() =>
    (window as any).__emitWsMessage({
      type: "termination",
      termination: {
        reason: "manual",
        terminatedAt: "2025-01-01T00:00:10Z",
      },
    })
  );

  await expect(page.locator("strong", { hasText: /session ended/i })).toBeVisible();
});
