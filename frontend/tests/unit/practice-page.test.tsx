import { describe, expect, it, vi } from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

import PracticePage from "../../app/practice/[sessionId]/page";

// Mock the child component to isolate the test to routing/rendering logic
vi.mock("../../app/practice/[sessionId]/phone-call-room", () => ({
  default: ({ sessionId }: { sessionId: string }) => (
    <div data-testid="mock-phone-call-room">PhoneCallRoom: {sessionId}</div>
  ),
}));

describe("PracticePage Routing", () => {
  it("renders PhoneCallRoom once params resolve", async () => {
    const paramsPromise = Promise.resolve({ sessionId: "test-session-123" });
    render(<PracticePage params={paramsPromise} />);

    // Initially should show Loading state
    expect(screen.getByText("Loading...")).toBeDefined();

    // After resolution, it should render the PhoneCallRoom exclusively
    await waitFor(() => {
      expect(screen.getByTestId("mock-phone-call-room")).toBeDefined();
    });
    expect(screen.getByText("PhoneCallRoom: test-session-123")).toBeDefined();
  });

  it("phonecallroom routing ignores deprecated disable flag", async () => {
    const originalDisableFlag = process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DISABLED;
    process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DISABLED = "1";

    try {
      const paramsPromise = Promise.resolve({ sessionId: "deprecated-flag-session" });
      render(<PracticePage params={paramsPromise} />);

      expect(screen.getByText("Loading...")).toBeDefined();

      await waitFor(() => {
        expect(screen.getByTestId("mock-phone-call-room")).toBeDefined();
      });
      expect(screen.getByText("PhoneCallRoom: deprecated-flag-session")).toBeDefined();
    } finally {
      if (originalDisableFlag === undefined) {
        delete process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DISABLED;
      } else {
        process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DISABLED = originalDisableFlag;
      }
    }
  });
});
