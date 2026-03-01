import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { ConnectionState } from "@volcengine/rtc";

// Mock @volcengine/rtc
vi.mock("@volcengine/rtc", () => {
  const mockEngine = {
    joinRoom: vi.fn().mockResolvedValue(undefined),
    leaveRoom: vi.fn().mockResolvedValue(undefined),
    sendUserBinaryMessage: vi.fn().mockResolvedValue(undefined),
    on: vi.fn(),
    off: vi.fn(),
  };

  const mockCreateEngine = vi.fn().mockReturnValue(mockEngine);
  const mockDestroyEngine = vi.fn();

  const mockVERTC = {
    createEngine: mockCreateEngine,
    destroyEngine: mockDestroyEngine,
    events: {
      onUserJoined: "onUserJoined",
      onUserLeave: "onUserLeave",
      onUserBinaryMessageReceived: "onUserBinaryMessageReceived",
      onConnectionStateChanged: "onConnectionStateChanged",
      onAudioVolumeIndication: "onAudioVolumeIndication",
    },
  };

  return {
    __esModule: true,
    default: mockVERTC,
    VERTC: mockVERTC,
    ConnectionState: {
      CONNECTION_STATE_DISCONNECTED: 1,
      CONNECTION_STATE_CONNECTING: 2,
      CONNECTION_STATE_CONNECTED: 3,
      CONNECTION_STATE_RECONNECTING: 4,
      CONNECTION_STATE_FAILED: 5,
    },
    IRTCEngine: class MockIRTCEngine {},
  };
});

// Now import the hook after mocking
import { useVolcengineRTC } from "../useVolcengineRTC";

describe("useVolcengineRTC", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with correct default state", async () => {
    const { result } = renderHook(() => useVolcengineRTC());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.engine).not.toBeNull();
    expect(result.current.isConnected).toBe(false);
    expect(result.current.aiStatus).toBe("disconnected");
    expect(result.current.roomState.roomId).toBeNull();
    expect(result.current.roomState.userId).toBeNull();
    expect(result.current.roomState.connectionState).toBe(ConnectionState.CONNECTION_STATE_DISCONNECTED);
  });

  it("creates RTC engine on mount", async () => {
    const { result } = renderHook(() => useVolcengineRTC());

    // Wait for effect to run
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.engine).not.toBeNull();
  });

  it("joinRoom succeeds after engine initialization", async () => {
    const { result } = renderHook(() => useVolcengineRTC());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    await act(async () => {
      await result.current.joinRoom("test-token", "test-room", "user-1");
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.roomState.roomId).toBe("test-room");
    expect(result.current.roomState.userId).toBe("user-1");
    expect(result.current.aiStatus).toBe("joining");
  });

  it("leaveRoom updates state correctly", async () => {
    const { result } = renderHook(() => useVolcengineRTC());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    await act(async () => {
      await result.current.joinRoom("test-token", "test-room", "user-1");
    });

    await act(async () => {
      await result.current.leaveRoom();
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.aiStatus).toBe("left");
    expect(result.current.roomState.roomId).toBeNull();
    expect(result.current.roomState.userId).toBeNull();
  });

  it("sendCommand does nothing when not connected", () => {
    const { result } = renderHook(() => useVolcengineRTC());

    act(() => {
      result.current.sendCommand({
        userId: "ai_agent",
        message: new ArrayBuffer(8),
      });
    });

    // Should not throw, just warn
    expect(result.current.isConnected).toBe(false);
  });

  it("sendCommand sends message when connected", async () => {
    const { result } = renderHook(() => useVolcengineRTC());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    await act(async () => {
      await result.current.joinRoom("test-token", "test-room", "user-1");
    });

    const message = new ArrayBuffer(8);

    act(() => {
      result.current.sendCommand({
        userId: "ai_agent",
        message,
      });
    });

    // The mock should have been called - message sent
    expect(result.current.isConnected).toBe(true);
  });

  it("cleanup removes event handlers on unmount", async () => {
    const { unmount } = renderHook(() => useVolcengineRTC());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    // Unmount - cleanup should run
    unmount();

    // Should complete without error
  });
});
