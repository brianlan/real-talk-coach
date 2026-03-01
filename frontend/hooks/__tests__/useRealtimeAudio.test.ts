import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { ConnectionState } from "@volcengine/rtc";

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

import { useRealtimeAudio } from "../useRealtimeAudio";

describe("useRealtimeAudio", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with correct default state", async () => {
    const { result } = renderHook(() => useRealtimeAudio());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.isListening).toBe(false);
    expect(result.current.isSpeaking).toBe(false);
    expect(result.current.isAiSpeaking).toBe(false);
    expect(result.current.isMuted).toBe(false);
  });

  it("toggleMute toggles muted state", async () => {
    const { result } = renderHook(() => useRealtimeAudio());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.isMuted).toBe(false);

    act(() => {
      result.current.toggleMute();
    });

    expect(result.current.isMuted).toBe(true);

    act(() => {
      result.current.toggleMute();
    });

    expect(result.current.isMuted).toBe(false);
  });

  it("setMute sets muted state directly", async () => {
    const { result } = renderHook(() => useRealtimeAudio());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    act(() => {
      result.current.setMute(true);
    });

    expect(result.current.isMuted).toBe(true);

    act(() => {
      result.current.setMute(false);
    });

    expect(result.current.isMuted).toBe(false);
  });

  it("resets audio state when disconnected", async () => {
    const { result, rerender } = renderHook(() => useRealtimeAudio());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    act(() => {
      result.current.setMute(true);
    });

    expect(result.current.isMuted).toBe(true);

    rerender();

    expect(result.current.isListening).toBe(false);
    expect(result.current.isSpeaking).toBe(false);
    expect(result.current.isAiSpeaking).toBe(false);
  });
});
